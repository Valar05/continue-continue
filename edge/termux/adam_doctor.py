#!/usr/bin/env python3
"""Deterministic readiness probe for the Adam phone daemon.

Adam owns the human-facing phone shell/Continue surface but never owns Ollama.
Vlad is the only component asked to prove Continue/Ollama readiness. Adam merely
records Vlad's receipt and its own shell/installation facts.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping

SCHEMA = "continue-continue.adam-doctor.v1"
DEFAULT_STATE = "~/.continue-continue/adam"


def _command_path(command: str, env: Mapping[str, str]) -> str | None:
    candidate = pathlib.Path(os.path.expanduser(command))
    if candidate.is_absolute() or "/" in command:
        return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
    return shutil.which(command, path=env.get("PATH"))


def _status(name: str, state: str, evidence: list[str], detail: str = "") -> dict[str, Any]:
    return {"name": name, "state": state, "evidence": evidence, "detail": detail}


def _invoke_vlad_doctor(env: Mapping[str, str]) -> tuple[str, dict[str, Any] | None, list[str]]:
    configured = env.get("ADAM_VLAD_BIN", "vlad")
    path = _command_path(configured, env)
    if not path:
        return "FAIL", None, [f"vlad:not-installed:{configured}"]
    completed = subprocess.run(
        [path, "--json", "doctor", "--require", "continue"],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
        env=dict(env),
    )
    evidence = [f"vlad:path={path}", f"vlad:doctor-exit={completed.returncode}"]
    try:
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise ValueError("doctor output is not an object")
    except Exception:
        text = (completed.stderr or completed.stdout).strip().replace("\n", " ")[:500]
        evidence.append("vlad:doctor-unparseable=" + text)
        return "UNKNOWN", None, evidence
    failures = payload.get("requiredFailures")
    if isinstance(failures, list):
        evidence.append("vlad:required-failures=" + ",".join(str(x) for x in failures))
    return ("PASS" if completed.returncode == 0 and payload.get("ready") is True else "FAIL"), payload, evidence


def diagnose(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    checks: list[dict[str, Any]] = []

    shell = env.get("ADAM_SHELL") or env.get("SHELL") or "sh"
    shell_path = _command_path(shell, env)
    checks.append(
        _status(
            "shell",
            "PASS" if shell_path else "FAIL",
            [f"shell:path={shell_path or 'missing'}"],
            "Adam owns shell dispatch; no model is involved.",
        )
    )

    adam_bin = env.get("ADAM_BIN", "adam")
    adam_path = _command_path(adam_bin, env)
    checks.append(
        _status(
            "adam_install",
            "PASS" if adam_path else "FAIL",
            [f"adam:path={adam_path or 'missing'}"],
            "Installed means a real command exists on PATH; repository code alone is not installation.",
        )
    )

    vlad_state, vlad_payload, vlad_evidence = _invoke_vlad_doctor(env)
    checks.append(
        _status(
            "vlad_continue",
            vlad_state,
            vlad_evidence,
            "Vlad owns Continue/Ollama readiness. Adam does not contact Ollama or perform inference.",
        )
    )

    ready = all(check["state"] == "PASS" for check in checks)
    state_root = pathlib.Path(os.path.expanduser(env.get("ADAM_STATE_DIR", DEFAULT_STATE)))
    state_root.mkdir(parents=True, exist_ok=True)
    receipt_path = state_root / "doctor-receipt.json"
    receipt = {
        "schema": SCHEMA,
        "createdAt": int(time.time() * 1000),
        "ready": ready,
        "statusVocabulary": ["requested", "implemented", "installed", "running", "proven", "blocked"],
        "ownership": {
            "adam": ["human interface", "shell dispatch", "Continue command surface", "phone hands routing", "policy", "receipts"],
            "vlad": ["Ollama", "model-backed judgment", "Continue model readiness"],
            "venice": ["optional adviser; never required for Adam readiness"],
        },
        "checks": checks,
        "vladReceipt": vlad_payload,
    }
    temp = receipt_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temp.replace(receipt_path)
    receipt["receiptPath"] = str(receipt_path)
    return receipt


def render_human(report: dict[str, Any]) -> str:
    lines = ["Adam READY" if report.get("ready") else "Adam BLOCKED"]
    for check in report.get("checks", []):
        lines.append(f"{check.get('state', 'UNKNOWN'):7} {check.get('name', '?')}: {check.get('detail', '')}")
        for evidence in check.get("evidence", []):
            lines.append(f"  {evidence}")
    lines.append(f"receipt={report.get('receiptPath', '?')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adam doctor", description="Prove Adam phone daemon readiness without model inference.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = diagnose()
    except OSError as exc:
        print(f"[blocked] {exc}", file=sys.stderr)
        return 3
    print(json.dumps(report, indent=2) if args.json else render_human(report))
    return 0 if report["ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
