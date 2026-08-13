#!/usr/bin/env python3
"""One durable Adam -> authenticated Codex worker bridge.

This bridge deliberately uses the Codex CLI's saved ChatGPT authentication.
It removes API-key environment variables, fails closed unless `codex login
status` reports ChatGPT authentication, persists JSONL events, and records the
thread ID needed for an exact resume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Iterable


def state_dir() -> pathlib.Path:
    root = pathlib.Path(os.path.expanduser(os.environ.get("ADAM_CODEX_STATE_DIR", "~/.continue-continue/adam/codex")))
    root.mkdir(parents=True, exist_ok=True)
    return root


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY"):
        env.pop(key, None)
    return env


def codex_bin() -> str:
    configured = os.environ.get("ADAM_CODEX_BIN", "codex")
    resolved = shutil.which(configured)
    if not resolved:
        raise RuntimeError(f"Codex CLI not found: {configured}")
    return resolved


def auth_status(binary: str) -> dict[str, Any]:
    completed = subprocess.run(
        [binary, "login", "status"],
        env=clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    summary = (completed.stdout + "\n" + completed.stderr).strip()
    mode = summary.lower()
    chatgpt = "chatgpt" in mode or "oauth" in mode
    return {
        "ok": completed.returncode == 0 and chatgpt,
        "returncode": completed.returncode,
        "chatgptAuth": chatgpt,
        "summary": summary[:500],
    }


def atomic_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def nested_values(value: Any, keys: set[str]) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and isinstance(child, str):
                yield child
            yield from nested_values(child, keys)
    elif isinstance(value, list):
        for child in value:
            yield from nested_values(child, keys)


def parse_event(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def invoke(prompt: str, cwd: pathlib.Path, session_id: str | None = None) -> int:
    binary = codex_bin()
    auth = auth_status(binary)
    if not auth["ok"]:
        print("[blocked] Codex CLI is not authenticated with ChatGPT OAuth.", file=sys.stderr)
        if auth["summary"]:
            print(auth["summary"], file=sys.stderr)
        return 3

    run_id = f"cw-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    run_dir = state_dir() / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    events_path = run_dir / "events.jsonl"
    final_path = run_dir / "final.txt"
    receipt_path = run_dir / "receipt.json"
    receipt: dict[str, Any] = {
        "schema": "continue-continue.adam-codex-worker.v1",
        "runId": run_id,
        "state": "RUNNING",
        "cwd": str(cwd),
        "promptSha256": prompt_hash(prompt),
        "requestedSessionId": session_id,
        "threadId": session_id,
        "auth": {"chatgptAuth": True, "apiKeyEnvironmentRemoved": True},
        "events": str(events_path),
        "final": str(final_path),
        "startedAtMs": int(time.time() * 1000),
    }
    atomic_json(receipt_path, receipt)

    command = [binary, "exec", "--json", "--sandbox", "workspace-write", "--cd", str(cwd)]
    configured_model = os.environ.get("ADAM_CODEX_MODEL")
    if configured_model:
        command.extend(["--model", configured_model])
    command.extend(["--output-last-message", str(final_path)])
    if session_id:
        command.extend(["resume", session_id, "-"])
    else:
        command.append("-")

    found_thread = session_id
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=clean_env(),
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        with events_path.open("w", encoding="utf-8") as events:
            for line in process.stdout:
                events.write(line)
                event = parse_event(line)
                if event:
                    candidates = list(nested_values(event, {"thread_id", "threadId", "session_id", "sessionId"}))
                    if candidates and not found_thread:
                        found_thread = candidates[0]
                sys.stdout.write(line)
        stderr = process.stderr.read() if process.stderr else ""
        returncode = process.wait()
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
    except BaseException as exc:
        receipt.update({"state": "RECOVERABLE", "error": str(exc), "threadId": found_thread})
        atomic_json(receipt_path, receipt)
        raise

    receipt.update(
        {
            "state": "COMPLETED_PRESERVED" if returncode == 0 else "BLOCKED",
            "returncode": returncode,
            "threadId": found_thread,
            "stderrTail": stderr[-2000:],
            "finishedAtMs": int(time.time() * 1000),
        }
    )
    atomic_json(receipt_path, receipt)
    latest = state_dir() / "latest.json"
    atomic_json(latest, receipt)
    if final_path.exists():
        sys.stdout.write(final_path.read_text(encoding="utf-8"))
        if final_path.stat().st_size and not final_path.read_bytes().endswith(b"\n"):
            sys.stdout.write("\n")
    print(json.dumps({"runId": run_id, "threadId": found_thread, "receipt": str(receipt_path), "state": receipt["state"]}, sort_keys=True))
    return returncode


def doctor(as_json: bool) -> int:
    try:
        binary = codex_bin()
        auth = auth_status(binary)
    except RuntimeError as exc:
        binary, auth = None, {"ok": False, "summary": str(exc), "chatgptAuth": False}
    payload = {
        "schema": "continue-continue.adam-codex-doctor.v1",
        "codex": binary,
        "auth": auth,
        "stateDir": str(state_dir()),
        "ready": bool(binary and auth.get("ok")),
    }
    print(json.dumps(payload, indent=2, sort_keys=True) if as_json else f"codex={binary or 'missing'} chatgpt_auth={auth.get('chatgptAuth', False)} ready={payload['ready']}")
    return 0 if payload["ready"] else 3


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adam codex", description="Run one resumable Codex worker using saved ChatGPT authentication")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--json", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("prompt")
    r.add_argument("--cwd", default=".")
    x = sub.add_parser("resume")
    x.add_argument("session_id")
    x.add_argument("prompt")
    x.add_argument("--cwd", default=".")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "doctor":
        return doctor(args.json)
    cwd = pathlib.Path(os.path.expanduser(args.cwd)).resolve()
    if not cwd.is_dir():
        print(f"[blocked] worker cwd is not a directory: {cwd}", file=sys.stderr)
        return 3
    return invoke(args.prompt, cwd, getattr(args, "session_id", None))


if __name__ == "__main__":
    raise SystemExit(main())
