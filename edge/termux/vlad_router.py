#!/usr/bin/env python3
"""Dumb spreadsheet-like ingress router for Vlad.

This is intentionally boring. It applies first-match CSV rules before a request
reaches the Vlad edge runtime. The sheet may classify or select a route, but it
never grants Phone Hands or local-exec permission; Vlad's existing gates remain
final authority.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import pathlib
import shlex
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

VALID_ROUTES = {"phone_hands", "shell", "delegate", "blocked", "passthrough"}
EXIT_SUCCESS = 0
EXIT_BAD_INVOCATION = 2
EXIT_BLOCKED = 3
EXIT_EXECUTION_FAILED = 4
EXIT_VERIFICATION_FAILED = 5


def here() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def default_sheet_path() -> pathlib.Path:
    override = os.environ.get("VLAD_ROUTING_SHEET")
    if override:
        return pathlib.Path(override)
    installed = here() / "continue-continue-vlad-routes.csv"
    return installed if installed.exists() else here() / "routes.csv"


def default_edge_path() -> pathlib.Path:
    override = os.environ.get("VLAD_EDGE_INTERNAL")
    if override:
        return pathlib.Path(override)
    installed = here() / "continue-continue-vlad-edge"
    return installed if installed.exists() else here() / "vlad_edge.py"


def load_edge(path: pathlib.Path | None = None):
    target = path or default_edge_path()
    spec = importlib.util.spec_from_file_location("continue_continue_vlad_edge", target)
    if not spec or not spec.loader:
        raise RuntimeError(f"could not load Vlad edge runtime from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def terms(value: str | None) -> list[str]:
    return [item.strip().lower() for item in str(value or "").split("|") if item.strip()]


def coerce_request(payload: dict[str, Any]) -> dict[str, Any]:
    task = dict(payload)
    request = task.pop("request", None)
    if not task.get("goal") and isinstance(request, str) and request.strip():
        task["goal"] = request.strip()
    if not task.get("goal"):
        raise ValueError("goal or request is required")
    task.setdefault("actor", "venice")
    task.setdefault("domain", "unsorted")
    task.setdefault("requestedOutcome", task["goal"])
    return task


def task_text(task: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ("goal", "requestedOutcome"):
        value = task.get(key)
        if isinstance(value, str):
            chunks.append(value)
    for key in ("constraints", "acceptanceCriteria", "preferredTools"):
        value = task.get(key)
        if isinstance(value, list):
            chunks.extend(str(item) for item in value)
    return "\n".join(chunks).lower()


def load_rules(sheet: pathlib.Path | None = None) -> list[dict[str, str]]:
    path = sheet or default_sheet_path()
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    rows = [row for row in rows if truthy(row.get("enabled"))]
    rows.sort(key=lambda row: int(row.get("priority") or 999999))
    return rows


def row_matches(row: dict[str, str], task: dict[str, Any]) -> bool:
    domain = str(row.get("domain") or "*").strip().lower()
    if domain not in {"", "*", str(task.get("domain", "")).lower()}:
        return False
    haystack = task_text(task)
    any_terms = terms(row.get("contains_any"))
    all_terms = terms(row.get("contains_all"))
    if any_terms and not any(term in haystack for term in any_terms):
        return False
    if all_terms and not all(term in haystack for term in all_terms):
        return False
    return bool(any_terms or all_terms or domain not in {"", "*"})


def render_cell(value: str | None, task: dict[str, Any]) -> str:
    text = str(value or "")
    return (
        text.replace("{goal}", str(task.get("goal", "")))
        .replace("{requestedOutcome}", str(task.get("requestedOutcome", "")))
        .replace("{domain}", str(task.get("domain", "")))
    )


def evaluate(task: dict[str, Any], sheet: pathlib.Path | None = None) -> dict[str, Any]:
    for row in load_rules(sheet):
        if not row_matches(row, task):
            continue
        route = str(row.get("route") or "passthrough").strip().lower()
        if route not in VALID_ROUTES:
            return {
                "matched": True,
                "rule": row.get("name") or "unnamed",
                "route": "blocked",
                "reason": f"routing sheet contains unsupported route: {route}",
            }
        result: dict[str, Any] = {
            "matched": True,
            "rule": row.get("name") or "unnamed",
            "route": route,
            "reason": row.get("reason") or "routing sheet match",
            "priority": int(row.get("priority") or 999999),
        }
        target_domain = str(row.get("target_domain") or "").strip().lower()
        if target_domain:
            result["targetDomain"] = target_domain
        if route == "phone_hands":
            result["action"] = {
                "kind": "phone_hands",
                "prompt": render_cell(row.get("phone_prompt"), task) or task["goal"],
            }
        elif route == "shell":
            command = render_cell(row.get("command"), task)
            if not command:
                return {
                    **result,
                    "route": "blocked",
                    "reason": "routing sheet shell row has no command",
                }
            result["action"] = {"kind": "shell", "argv": shlex.split(command)}
        elif route in {"delegate", "blocked"}:
            result["action"] = {"kind": route}
        return result
    return {
        "matched": False,
        "rule": None,
        "route": "passthrough",
        "reason": "no routing-sheet row matched",
    }


def apply_sheet(payload: dict[str, Any], sheet: pathlib.Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    task = coerce_request(payload)
    context = dict(task.get("context") or {})
    edge = context.get("edge")
    if isinstance(edge, dict) and isinstance(edge.get("action"), dict):
        decision = {
            "matched": False,
            "rule": None,
            "route": "explicit",
            "reason": "caller supplied explicit edge action; routing sheet did not override it",
        }
        context["routingSheet"] = decision
        task["context"] = context
        return task, decision

    decision = evaluate(task, sheet)
    if decision.get("targetDomain"):
        task["domain"] = decision["targetDomain"]
    context["routingSheet"] = {
        key: value for key, value in decision.items() if key != "action"
    }
    action = decision.get("action")
    if action:
        edge_context = dict(context.get("edge") or {})
        edge_context["action"] = action
        context["edge"] = edge_context
    task["context"] = context
    return task, decision


def exit_code_for_status(status: str) -> int:
    if status in {"completed", "delegated"}:
        return EXIT_SUCCESS
    if status == "blocked":
        return EXIT_BLOCKED
    if status in {"failed", "cancelled"}:
        return EXIT_EXECUTION_FAILED
    return EXIT_VERIFICATION_FAILED


def make_handler(edge, sheet: pathlib.Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ContinueContinueVladRouter/0.1"

        def _json(self, code: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be an object")
            return payload

        def do_GET(self) -> None:  # noqa: N802
            parts = self.path.strip("/").split("/")
            if self.path == "/automation/capabilities":
                capabilities = edge.capabilities()
                capabilities["ingressRouter"] = {
                    "kind": "csv-first-match",
                    "sheet": str(sheet),
                    "rules": len(load_rules(sheet)),
                    "qwenFallback": True,
                }
                self._json(200, capabilities)
                return
            if self.path == "/automation/tasks":
                self._json(200, {"runtime": "vlad-edge", "tasks": edge.list_tasks()})
                return
            if len(parts) >= 3 and parts[:2] == ["automation", "tasks"]:
                record = edge.load(parts[2])
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
            if self.path == "/routing/preview":
                try:
                    task, decision = apply_sheet(self._body(), sheet)
                    self._json(200, {"decision": decision, "task": task})
                except (ValueError, json.JSONDecodeError) as exc:
                    self._json(400, {"error": str(exc)})
                return
            if self.path != "/automation/tasks":
                self._json(404, {"error": "not found"})
                return
            try:
                routed, decision = apply_sheet(self._body(), sheet)
                record = edge.create_record(routed)
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
                return
            threading.Thread(target=edge.execute, args=(record,), daemon=True).start()
            self._json(202, {"queued": True, "routing": decision, "task": record})

        def log_message(self, fmt: str, *args: Any) -> None:
            if os.environ.get("VLAD_EDGE_QUIET") != "1":
                super().log_message(fmt, *args)

    return Handler


def read_payload(source: str) -> dict[str, Any]:
    if source == "-":
        payload = json.load(sys.stdin)
    else:
        payload = json.loads(pathlib.Path(source).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request input must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Spreadsheet ingress router for Vlad")
    parser.add_argument("--sheet", type=pathlib.Path, default=default_sheet_path())
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="route and run one request")
    run_p.add_argument("task", help="task/request JSON file or - for stdin")
    route_p = sub.add_parser("route", help="preview routing without executing")
    route_p.add_argument("task", help="task/request JSON file or - for stdin")
    serve_p = sub.add_parser("serve", help="serve routed machine-task HTTP API")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8765)
    sub.add_parser("capabilities", help="print routed edge capabilities")
    args = parser.parse_args()

    edge = load_edge()
    if args.command == "route":
        task, decision = apply_sheet(read_payload(args.task), args.sheet)
        print(json.dumps({"decision": decision, "task": task}, indent=2))
        return EXIT_SUCCESS
    if args.command == "run":
        try:
            routed, decision = apply_sheet(read_payload(args.task), args.sheet)
            record = edge.create_record(routed)
            result = edge.execute(record)
            print(json.dumps({"routing": decision, "receipt": result.get("receipt") or result}, indent=2))
            return exit_code_for_status(result["status"])
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return EXIT_BAD_INVOCATION
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return EXIT_EXECUTION_FAILED
    if args.command == "capabilities":
        capabilities = edge.capabilities()
        capabilities["ingressRouter"] = {
            "kind": "csv-first-match",
            "sheet": str(args.sheet),
            "rules": len(load_rules(args.sheet)),
            "qwenFallback": True,
        }
        print(json.dumps(capabilities, indent=2))
        return EXIT_SUCCESS

    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(edge, args.sheet)
    )
    print(f"Vlad routing ingress listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
