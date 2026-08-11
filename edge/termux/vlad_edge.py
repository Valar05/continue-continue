#!/usr/bin/env python3
"""Tiny Termux edge runtime for Continue Continue / Vlad.

Stdlib-only by design. It accepts the same machine-task envelope as the full
runtime, persists receipts locally, and routes work to explicitly enabled phone
organs or to a configured upstream Continue Continue service.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

TASK_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
TERMINAL = {"completed", "blocked", "delegated", "failed", "cancelled"}
PHONE_ASK_DEFAULT = "/data/data/com.termux/files/usr/local/bin/home-center-phone-ask"
DEFAULT_ALLOWED_BINS = "cn,git,ffmpeg,ffprobe,python,python3,node,npm,npx,rg,grep,find,ls,pwd,cat,mkdir,cp"


def now_ms() -> int:
    return int(time.time() * 1000)


def root_dir() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get(
            "CONTINUE_CONTINUE_EDGE_DIR",
            pathlib.Path.home() / ".continue-continue" / "vlad",
        )
    )


def task_dir() -> pathlib.Path:
    path = root_dir() / "tasks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _text(value: Any, name: str, limit: int = 8000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{name} exceeds {limit} characters")
    return value


def _strings(value: Any, name: str, limit: int = 32) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be an array of at most {limit} strings")
    return [_text(item, f"{name}[]", 2000) for item in value]


def normalize_task(payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("taskId") or uuid.uuid4())
    if not (3 <= len(task_id) <= 160) or any(c not in TASK_ID_CHARS for c in task_id):
        raise ValueError("taskId must be a safe 3-160 character identifier")
    domain = _text(payload.get("domain"), "domain", 64).lower()
    if not domain[0].isalpha() or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in domain):
        raise ValueError("domain must be a lowercase routing slug")
    goal = _text(payload.get("goal"), "goal")
    criteria = _strings(payload.get("acceptanceCriteria"), "acceptanceCriteria")
    if not criteria:
        criteria = [
            "Return a truthful receipt naming the delivered result or exact blocking boundary."
        ]
    context = payload.get("context") or {}
    if not isinstance(context, dict):
        raise ValueError("context must be an object")
    encoded_context = json.dumps(context, separators=(",", ":"))
    if len(encoded_context.encode("utf-8")) > 32768:
        raise ValueError("context exceeds 32768 bytes")
    priority = payload.get("priority", "normal")
    if priority not in {"low", "normal", "high"}:
        raise ValueError("priority must be low, normal, or high")
    return {
        "taskId": task_id,
        "actor": _text(payload.get("actor", "vlad"), "actor", 120),
        "domain": domain,
        "goal": goal,
        "requestedOutcome": _text(payload.get("requestedOutcome", goal), "requestedOutcome"),
        "acceptanceCriteria": criteria,
        "constraints": _strings(payload.get("constraints"), "constraints"),
        "preferredTools": _strings(payload.get("preferredTools"), "preferredTools"),
        "lane": payload.get("lane"),
        "priority": priority,
        "context": context,
    }


def task_path(task_id: str) -> pathlib.Path:
    return task_dir() / f"{task_id}.json"


def save(record: dict[str, Any]) -> None:
    target = task_path(record["taskId"])
    temp = target.with_suffix(f".json.{os.getpid()}.tmp")
    temp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


def load(task_id: str) -> dict[str, Any] | None:
    path = task_path(task_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_tasks() -> list[dict[str, Any]]:
    result = []
    for path in sorted(task_dir().glob("*.json")):
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sorted(result, key=lambda item: item.get("createdAt", 0))


def enabled(name: str) -> bool:
    return os.environ.get(name, "0") == "1"


def explicit_edge_action(task: dict[str, Any]) -> dict[str, Any] | None:
    edge = task.get("context", {}).get("edge")
    if isinstance(edge, dict) and isinstance(edge.get("action"), dict):
        return edge["action"]
    return None


def qwen_route(task: dict[str, Any]) -> dict[str, Any] | None:
    base = os.environ.get("QWEN_BASE_URL")
    if not base:
        return None
    model = os.environ.get("QWEN_MODEL", "Qwen3-1.7B-Q6_K")
    prompt = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Route a phone edge machine task. Return JSON only with route equal to "
                    "phone_hands, delegate, or blocked. You do not grant permission and may not "
                    "invent completion. phone_hands is for Android UI/device actions; delegate is "
                    "for heavy or unavailable work. Include reason and optional phonePrompt."
                ),
            },
            {"role": "user", "content": json.dumps(task, separators=(",", ":"))},
        ],
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(prompt).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        text = data["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        route = json.loads(text)
        if route.get("route") not in {"phone_hands", "delegate", "blocked"}:
            return None
        return route
    except Exception:
        return None


def choose_route(task: dict[str, Any]) -> dict[str, Any]:
    action = explicit_edge_action(task)
    if action:
        kind = action.get("kind")
        if kind in {"phone_hands", "shell", "delegate", "blocked"}:
            return {"route": kind, "action": action, "reason": "explicit edge action"}
        return {"route": "blocked", "reason": f"unsupported explicit edge action: {kind}"}

    planned = qwen_route(task)
    if planned:
        return planned

    if "phone_hands" in task.get("preferredTools", []):
        return {"route": "phone_hands", "phonePrompt": task["goal"], "reason": "preferred tool"}
    if os.environ.get("CONTINUE_CONTINUE_UPSTREAM_URL"):
        return {"route": "delegate", "reason": "full runtime configured"}
    return {
        "route": "blocked",
        "reason": "no explicit local action and no configured upstream runtime",
    }


def finish(record: dict[str, Any], status: str, summary: str, evidence: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    if status not in TERMINAL:
        raise ValueError(f"invalid terminal status: {status}")
    record.update(extra)
    record["status"] = status
    record["resultSummary"] = summary
    record["evidence"] = evidence or []
    record["updatedAt"] = now_ms()
    record["completedAt"] = record["updatedAt"]
    record["receipt"] = {
        "taskId": record["taskId"],
        "actor": record["actor"],
        "domain": record["domain"],
        "status": status,
        "requestedOutcome": record["requestedOutcome"],
        "acceptanceCriteria": record["acceptanceCriteria"],
        "resultSummary": summary,
        "evidence": record["evidence"],
        "delegateTarget": record.get("delegateTarget"),
        "error": record.get("error"),
        "createdAt": record["createdAt"],
        "startedAt": record.get("startedAt"),
        "completedAt": record["completedAt"],
    }
    save(record)
    return record


def run_phone_hands(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    if not enabled("VLAD_ALLOW_PHONE_HANDS"):
        return finish(record, "blocked", "Phone Hands permission is disabled.", ["gate:VLAD_ALLOW_PHONE_HANDS=0"])
    action = route.get("action") or {}
    prompt = action.get("prompt") or route.get("phonePrompt") or record["goal"]
    binary = os.environ.get("PHONE_ASK_BIN", PHONE_ASK_DEFAULT)
    try:
        completed = subprocess.run(
            [binary, str(prompt)], capture_output=True, text=True, timeout=90, check=False
        )
    except Exception as exc:
        record["error"] = str(exc)
        return finish(record, "failed", "Phone Hands invocation failed.", [f"phone_ask:{binary}"], error=str(exc))
    evidence = [f"phone_ask:exit={completed.returncode}"]
    if completed.stdout.strip():
        evidence.append("phone_ask:stdout=" + completed.stdout.strip()[:2000])
    if completed.returncode != 0:
        error = completed.stderr.strip() or "Phone Hands returned nonzero"
        record["error"] = error
        return finish(record, "failed", "Phone Hands returned an error.", evidence, error=error)
    return finish(record, "completed", "Phone Hands completed the requested phone action.", evidence)


def _shell_allowed_bins(action: dict[str, Any]) -> tuple[set[str] | None, str | None]:
    policy = set(
        filter(
            None,
            os.environ.get("VLAD_ALLOWED_BINS", DEFAULT_ALLOWED_BINS).split(","),
        )
    )
    requested = action.get("allowedBins")
    if requested is None:
        return policy, None
    if not isinstance(requested, list) or not requested or not all(
        isinstance(item, str) and item.strip() for item in requested
    ):
        return None, "edge.action.allowedBins must be a non-empty string array when provided"
    narrowed = {pathlib.Path(item.strip()).name for item in requested}
    return policy & narrowed, None


def run_shell(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    if not enabled("VLAD_ALLOW_LOCAL_EXEC"):
        return finish(record, "blocked", "Local command execution is disabled.", ["gate:VLAD_ALLOW_LOCAL_EXEC=0"])
    action = route.get("action") or {}
    argv = action.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        return finish(record, "blocked", "Explicit shell action requires argv as a non-empty string array.", ["contract:edge.action.argv"])
    allowed, allowed_error = _shell_allowed_bins(action)
    if allowed_error:
        return finish(record, "blocked", allowed_error, ["contract:edge.action.allowedBins"])
    assert allowed is not None
    binary = pathlib.Path(argv[0]).name
    if binary not in allowed:
        return finish(record, "blocked", f"Binary {binary} is not allowed by Vlad edge policy for this task.", [f"allowed_bins:{','.join(sorted(allowed))}"])
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
    evidence = [f"shell:{binary}:exit={completed.returncode}", f"shell:allowed_bins={','.join(sorted(allowed))}"]
    if completed.stdout.strip():
        evidence.append("stdout=" + completed.stdout.strip()[:2000])
    if completed.returncode != 0:
        error = completed.stderr.strip() or f"{binary} returned {completed.returncode}"
        record["error"] = error
        return finish(record, "failed", "Local edge command failed.", evidence, error=error)
    return finish(record, "completed", "Local edge command completed.", evidence)


def delegate(record: dict[str, Any]) -> dict[str, Any]:
    upstream = os.environ.get("CONTINUE_CONTINUE_UPSTREAM_URL")
    if not upstream:
        return finish(record, "blocked", "No upstream Continue Continue runtime is configured.", ["missing:CONTINUE_CONTINUE_UPSTREAM_URL"])
    task_payload = {key: record[key] for key in ("taskId", "actor", "domain", "goal", "requestedOutcome", "acceptanceCriteria", "constraints", "preferredTools", "lane", "priority", "context")}
    req = urllib.request.Request(
        upstream.rstrip("/") + "/automation/tasks",
        data=json.dumps(task_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        record["error"] = str(exc)
        return finish(record, "failed", "Delegation request failed.", [f"upstream:{upstream}"], error=str(exc))
    returned_id = payload.get("task", {}).get("taskId") or record["taskId"]
    return finish(
        record,
        "delegated",
        "Task was handed to the configured full Continue Continue runtime; requested outcome is not yet complete.",
        [f"upstream:{upstream}", f"upstream-task:{returned_id}"],
        delegateTarget=upstream,
    )


def execute(record: dict[str, Any]) -> dict[str, Any]:
    record["status"] = "running"
    record["startedAt"] = record.get("startedAt") or now_ms()
    record["updatedAt"] = now_ms()
    save(record)
    route = choose_route(record)
    record["route"] = route.get("route")
    record["routeReason"] = route.get("reason")
    save(record)
    if route["route"] == "phone_hands":
        return run_phone_hands(record, route)
    if route["route"] == "shell":
        return run_shell(record, route)
    if route["route"] == "delegate":
        return delegate(record)
    return finish(record, "blocked", route.get("reason", "No safe route is available."), ["route:blocked"])


def create_record(payload: dict[str, Any]) -> dict[str, Any]:
    task = normalize_task(payload)
    if load(task["taskId"]):
        raise ValueError(f"task {task['taskId']} already exists")
    created = now_ms()
    record = {**task, "status": "queued", "createdAt": created, "updatedAt": created, "evidence": []}
    save(record)
    return record


class Handler(BaseHTTPRequestHandler):
    server_version = "ContinueContinueVlad/0.1"

    def _json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(data, dict):
            raise ValueError("request body must be an object")
        return data

    def do_GET(self) -> None:  # noqa: N802
        parts = self.path.strip("/").split("/")
        if self.path == "/automation/capabilities":
            self._json(200, capabilities())
            return
        if self.path == "/automation/tasks":
            self._json(200, {"runtime": "vlad-edge", "tasks": list_tasks()})
            return
        if len(parts) >= 3 and parts[:2] == ["automation", "tasks"]:
            record = load(parts[2])
            if not record:
                self._json(404, {"error": "task not found"})
                return
            if len(parts) == 4 and parts[3] == "receipt":
                receipt = record.get("receipt")
                self._json(200 if receipt else 409, receipt or {"error": "task does not have a terminal receipt", "status": record["status"]})
                return
            self._json(200, record)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/automation/tasks":
            self._json(404, {"error": "not found"})
            return
        try:
            record = create_record(self._body())
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        threading.Thread(target=execute, args=(record,), daemon=True).start()
        self._json(202, {"queued": True, "task": record})

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("VLAD_EDGE_QUIET") != "1":
            super().log_message(fmt, *args)


def capabilities() -> dict[str, Any]:
    return {
        "runtime": "vlad-edge",
        "domains": "open",
        "routes": ["phone_hands", "shell", "delegate", "blocked"],
        "phoneHands": {"enabled": enabled("VLAD_ALLOW_PHONE_HANDS"), "binary": os.environ.get("PHONE_ASK_BIN", PHONE_ASK_DEFAULT)},
        "localExec": {"enabled": enabled("VLAD_ALLOW_LOCAL_EXEC"), "allowedBins": sorted(set(filter(None, os.environ.get("VLAD_ALLOWED_BINS", DEFAULT_ALLOWED_BINS).split(","))))},
        "delegation": {"configured": bool(os.environ.get("CONTINUE_CONTINUE_UPSTREAM_URL"))},
        "qwenRouter": {"configured": bool(os.environ.get("QWEN_BASE_URL")), "model": os.environ.get("QWEN_MODEL", "Qwen3-1.7B-Q6_K")},
        "notes": ["Task intent never grants Phone Hands or shell permission.", "Per-task allowedBins can only narrow the governing shell policy.", "Delegated is a handoff receipt, not completion."],
    }


def read_task(source: str) -> dict[str, Any]:
    if source == "-":
        payload = json.load(sys.stdin)
    else:
        payload = json.loads(pathlib.Path(source).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("task input must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Continue Continue Vlad Termux edge")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run one machine task")
    run_p.add_argument("task", help="task JSON file or - for stdin")
    serve_p = sub.add_parser("serve", help="serve the machine-task HTTP API")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8765)
    sub.add_parser("capabilities", help="print edge capabilities")
    args = parser.parse_args()

    if args.command == "capabilities":
        print(json.dumps(capabilities(), indent=2))
        return 0
    if args.command == "run":
        try:
            record = create_record(read_task(args.task))
            result = execute(record)
            print(json.dumps(result.get("receipt") or result, indent=2))
            return 0 if result["status"] in {"completed", "delegated", "blocked"} else 1
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 2
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Vlad edge listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
