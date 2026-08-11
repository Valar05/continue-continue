#!/usr/bin/env python3
"""Human-facing Vlad CLI.

`continue-continue-vlad` remains the machine/routing entrypoint. `vlad` is the
survival/operator surface: natural-language one shots, a tiny REPL, deterministic
phone shortcuts, and an explicit Continue coding seam. It never bypasses the
edge permission gates; even explicit code/phone commands are merely authority
packets that the edge may block.

The canonical default Continue argv begins ["cn", "-p"]. VLAD_CN_BIN may
replace only the executable path; policy checks operate on its basename.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import uuid
from typing import Any

SCHEMA = "continue-continue.vlad-cli.v1"
DOCTOR_REQUIREMENTS = ("continue", "phone_hands", "qwen", "upstream")


def here() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def machine_command() -> list[str]:
    override = os.environ.get("VLAD_MACHINE_BIN")
    if override:
        return [override]
    installed = here() / "continue-continue-vlad"
    if installed.exists() and installed.name != pathlib.Path(__file__).name:
        return [str(installed)]
    router = here() / "vlad_router.py"
    return [sys.executable, str(router)]


def doctor_command() -> list[str]:
    override = os.environ.get("VLAD_DOCTOR_BIN")
    if override:
        return [override]
    installed = here() / "continue-continue-vlad-doctor"
    if installed.exists():
        return [str(installed)]
    return [sys.executable, str(here() / "vlad_doctor.py")]


def task_id(prefix: str = "vlad") -> str:
    return f"{prefix}:{uuid.uuid4().hex[:16]}"


def base_task(goal: str, domain: str = "unsorted") -> dict[str, Any]:
    text = str(goal or "").strip()
    if not text:
        raise ValueError("request is empty")
    return {
        "taskId": task_id(),
        "actor": os.environ.get("VLAD_ACTOR", "drew"),
        "domain": domain,
        "goal": text,
        "requestedOutcome": text,
        "acceptanceCriteria": [
            "Return a truthful receipt naming the delivered result or exact blocking boundary."
        ],
        "context": {"vladCli": {"schema": SCHEMA}},
    }


def explicit_phone_task(prompt: str) -> dict[str, Any]:
    task = base_task(prompt, "system")
    task["context"]["edge"] = {
        "action": {"kind": "phone_hands", "prompt": task["goal"]}
    }
    return task


def continue_task(
    prompt: str,
    *,
    readonly: bool = False,
    auto: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    if readonly and auto:
        raise ValueError("Continue task cannot be both readonly and auto")
    task = base_task(prompt, "code")
    configured_cn = os.environ.get("VLAD_CN_BIN", "cn")
    argv = [configured_cn, "-p"]
    if readonly:
        argv.append("--readonly")
    if auto:
        argv.append("--auto")
    if resume:
        argv.append("--resume")
    argv.append(task["goal"])
    # allowedBins is a per-task *narrowing* request. The edge intersects it with
    # its governing VLAD_ALLOWED_BINS policy, so this can never grant cn when
    # the global policy excludes it.
    task["context"]["edge"] = {
        "action": {
            "kind": "shell",
            "argv": argv,
            "allowedBins": [pathlib.Path(configured_cn).name],
        }
    }
    task["context"]["vladCli"].update(
        {"surface": "continue", "readonly": readonly, "auto": auto, "resume": resume}
    )
    task["constraints"] = [
        "Continue is the requested coding organ; do not substitute another coding agent.",
        "This task narrows shell authority to the configured Continue binary only.",
        "Completion requires the edge receipt; a model turn alone is not deployment evidence.",
    ]
    return task


def invoke_machine(
    mode: str, payload: dict[str, Any], *, capture: bool = True
) -> subprocess.CompletedProcess[str]:
    command = [*machine_command(), mode, "-"]
    return subprocess.run(
        command,
        input=json.dumps(payload),
        text=True,
        capture_output=capture,
        check=False,
    )


def parse_json_output(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def receipt_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("receipt")
    return value if isinstance(value, dict) else payload


def render_human(payload: dict[str, Any]) -> str:
    receipt = receipt_from_payload(payload)
    status_value = str(receipt.get("status") or payload.get("status") or "unknown")
    summary = str(receipt.get("resultSummary") or payload.get("resultSummary") or "")
    route = payload.get("routing")
    route_text = ""
    if isinstance(route, dict):
        route_text = str(route.get("route") or "")
    lines = [f"[{status_value}]" + (f" route={route_text}" if route_text else "")]
    if summary:
        lines.append(summary)
    evidence = receipt.get("evidence")
    if isinstance(evidence, list):
        lines.extend(f"- {item}" for item in evidence if str(item).strip())
    error = receipt.get("error") or payload.get("error")
    if error:
        lines.append(f"error: {error}")
    return "\n".join(lines)


def run_task(payload: dict[str, Any], *, json_output: bool) -> int:
    completed = invoke_machine("run", payload)
    stdout = completed.stdout.strip()
    parsed = parse_json_output(stdout)
    if json_output or not parsed:
        if completed.stdout:
            sys.stdout.write(completed.stdout)
        if completed.stderr:
            sys.stderr.write(completed.stderr)
    else:
        print(render_human(parsed))
        if completed.stderr:
            sys.stderr.write(completed.stderr)
    return completed.returncode


def route_request(request: str, *, json_output: bool = True) -> int:
    completed = invoke_machine("route", {"request": request})
    if completed.stdout:
        if json_output:
            sys.stdout.write(completed.stdout)
        else:
            parsed = parse_json_output(completed.stdout)
            if parsed:
                decision = parsed.get("decision") or {}
                print(
                    f"route={decision.get('route', 'unknown')} "
                    f"rule={decision.get('rule') or '-'} "
                    f"reason={decision.get('reason') or '-'}"
                )
            else:
                sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode


def run_doctor(requirements: list[str], *, json_output: bool) -> int:
    command = doctor_command()
    for requirement in requirements:
        command.extend(["--require", requirement])
    if not json_output:
        command.append("--pretty")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return 0 if completed.returncode == 0 else (3 if completed.returncode == 2 else completed.returncode)


def _doctor_check(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return None
    for check in checks:
        if isinstance(check, dict) and check.get("name") == name:
            return check
    return None


def status(json_output: bool) -> int:
    doctor = subprocess.run(doctor_command(), text=True, capture_output=True, check=False)
    caps = subprocess.run(
        [*machine_command(), "capabilities"], text=True, capture_output=True, check=False
    )
    doctor_payload = parse_json_output(doctor.stdout) or {
        "ready": False,
        "error": doctor.stderr.strip() or doctor.stdout.strip(),
    }
    caps_payload = parse_json_output(caps.stdout) or {
        "error": caps.stderr.strip() or caps.stdout.strip()
    }
    continue_binary = _doctor_check(doctor_payload, "continue_binary") or {}
    continue_policy = _doctor_check(doctor_payload, "continue_policy") or {}
    continue_permission = _doctor_check(doctor_payload, "continue_permission") or {}
    payload = {
        "schema": SCHEMA,
        "ready": bool(doctor_payload.get("ready")),
        "doctor": doctor_payload,
        "capabilities": caps_payload,
        "continue": {
            "configuredBinary": os.environ.get("VLAD_CN_BIN", "cn"),
            "available": bool(continue_binary.get("ok")),
            "policyAllowed": bool(continue_policy.get("ok")),
            "executionGate": bool(continue_permission.get("ok")),
            "note": "Code/review uses per-task allowedBins narrowing and still requires the governing Vlad edge policy and local-exec gate.",
        },
    }
    if json_output:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Vlad {'READY' if payload['ready'] else 'BLOCKED'}")
        print(
            "phone_hands="
            + str((caps_payload.get("phoneHands") or {}).get("enabled", False)).lower()
        )
        print(
            "local_exec="
            + str((caps_payload.get("localExec") or {}).get("enabled", False)).lower()
        )
        print(
            "continue="
            + (
                "ready"
                if payload["continue"]["available"]
                and payload["continue"]["policyAllowed"]
                and payload["continue"]["executionGate"]
                else "not-ready"
            )
        )
        print(
            "qwen_router="
            + str((caps_payload.get("qwenRouter") or {}).get("configured", False)).lower()
        )
    return 0 if payload["ready"] else 3


def repl() -> int:
    print("Vlad local. /quit exits; /doctor, /route, /code, /review, /new are available.")
    continue_session_started = False
    while True:
        try:
            line = input("vlad> ")
        except EOFError:
            return 0
        text = line.strip()
        if not text:
            continue
        if text in {"/quit", "/exit"}:
            return 0
        if text == "/doctor":
            run_doctor([], json_output=False)
            continue
        if text == "/new":
            continue_session_started = False
            print("Continue session reset; next /code or /review starts a fresh headless session.")
            continue
        if text.startswith("/route "):
            route_request(text[7:].strip(), json_output=False)
            continue
        if text.startswith("/code "):
            code = run_task(
                continue_task(text[6:].strip(), resume=continue_session_started),
                json_output=False,
            )
            if code == 0:
                continue_session_started = True
            continue
        if text.startswith("/review "):
            code = run_task(
                continue_task(
                    text[8:].strip(), readonly=True, resume=continue_session_started
                ),
                json_output=False,
            )
            if code == 0:
                continue_session_started = True
            continue
        run_task({"request": text}, json_output=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vlad",
        description="Local machine/operator CLI backed by Continue Continue Vlad edge.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="show readiness and exit 3 when blocked")
    doctor.add_argument(
        "--require",
        action="append",
        choices=DOCTOR_REQUIREMENTS,
        default=[],
        help="capability that must be runnable; may be repeated",
    )
    sub.add_parser("status", help="show readiness plus configured organs")

    route = sub.add_parser("route", help="preview spreadsheet routing without execution")
    route.add_argument("request", nargs="+")

    run = sub.add_parser("run", help="run a natural-language machine request")
    run.add_argument("request", nargs="+")

    ask = sub.add_parser("ask", help="alias for run")
    ask.add_argument("request", nargs="+")

    phone = sub.add_parser("phone", help="explicit Phone Hands request; still permission-gated")
    phone.add_argument("request", nargs="+")

    sub.add_parser("observe", help="explicit read-only phone observation request")
    sub.add_parser("home", help="explicit phone Home navigation request")

    code = sub.add_parser("code", help="invoke the configured Continue cn coding organ")
    code.add_argument("prompt", nargs="+")
    code.add_argument("--auto", action="store_true", help="pass --auto to cn; Vlad edge gate still applies")
    code.add_argument("--resume", action="store_true", help="resume the last Continue session in headless mode")

    review = sub.add_parser("review", help="invoke Continue in readonly review mode")
    review.add_argument("prompt", nargs="+")
    review.add_argument("--resume", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {"doctor", "status", "route", "run", "ask", "phone", "observe", "home", "code", "review", "-h", "--help"}
    filtered = [arg for arg in argv if arg != "--json"]
    if not filtered:
        return repl()
    if filtered[0] not in known and not filtered[0].startswith("-"):
        json_output = "--json" in argv
        request = " ".join(filtered).strip()
        return run_task({"request": request}, json_output=json_output)

    parser = build_parser()
    args = parser.parse_args(argv)
    json_output = bool(args.json)
    if args.command == "doctor":
        return run_doctor(args.require, json_output=json_output)
    if args.command == "status":
        return status(json_output)
    if args.command == "route":
        return route_request(" ".join(args.request), json_output=json_output)
    if args.command in {"run", "ask"}:
        return run_task({"request": " ".join(args.request)}, json_output=json_output)
    if args.command == "phone":
        return run_task(explicit_phone_task(" ".join(args.request)), json_output=json_output)
    if args.command == "observe":
        return run_task(
            explicit_phone_task("Observe only and tell me the current foreground app and screen state."),
            json_output=json_output,
        )
    if args.command == "home":
        return run_task(explicit_phone_task("Go home."), json_output=json_output)
    if args.command == "code":
        return run_task(
            continue_task(" ".join(args.prompt), auto=args.auto, resume=args.resume),
            json_output=json_output,
        )
    if args.command == "review":
        return run_task(
            continue_task(" ".join(args.prompt), readonly=True, resume=args.resume),
            json_output=json_output,
        )
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
