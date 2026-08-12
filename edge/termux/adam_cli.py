#!/usr/bin/env python3
"""Adam: deterministic phone-facing command surface.

Adam does not perform model inference. It owns the prompt, shell dispatch,
Continue/Vlad invocation, and receipts. Vlad remains the model-bearing helper.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import subprocess
import sys


def here() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def doctor_command() -> list[str]:
    override = os.environ.get("ADAM_DOCTOR_BIN")
    if override:
        return [override]
    installed = here() / "continue-continue-adam-doctor"
    if installed.exists():
        return [str(installed)]
    return [sys.executable, str(here() / "adam_doctor.py")]


def vlad_command() -> list[str]:
    return [os.environ.get("ADAM_VLAD_BIN", "vlad")]


def shell_command(command: str) -> int:
    shell = os.environ.get("ADAM_SHELL") or os.environ.get("SHELL") or "sh"
    return subprocess.run([shell, "-lc", command], check=False).returncode


def vlad(args: list[str]) -> int:
    return subprocess.run([*vlad_command(), *args], check=False).returncode


def repl() -> int:
    print("Adam local. No model. !shell, /code, /review, /doctor, /vlad, /quit.")
    while True:
        try:
            line = input("adam> ")
        except EOFError:
            return 0
        text = line.strip()
        if not text:
            continue
        if text in {"/quit", "/exit"}:
            return 0
        if text == "/doctor":
            subprocess.run(doctor_command(), check=False)
            continue
        if text.startswith("!"):
            shell_command(text[1:].lstrip())
            continue
        if text.startswith("/code "):
            vlad(["code", text[6:].strip()])
            continue
        if text.startswith("/review "):
            vlad(["review", text[8:].strip()])
            continue
        if text.startswith("/vlad "):
            vlad(shlex.split(text[6:].strip()))
            continue
        print("[blocked] Adam has no inference route for free-form chat yet. Use an explicit command or configure a deterministic rule.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return repl()
    if argv[0] == "doctor":
        return subprocess.run([*doctor_command(), *argv[1:]], check=False).returncode
    if argv[0] == "shell":
        if len(argv) < 2:
            print("adam shell requires a command", file=sys.stderr)
            return 2
        return shell_command(" ".join(argv[1:]))
    if argv[0] in {"code", "review", "status", "route", "phone", "observe", "home"}:
        return vlad(argv)
    if argv[0] in {"-h", "--help", "help"}:
        print("usage: adam [doctor|shell CMD|code PROMPT|review PROMPT|status|route ...|phone ...|observe|home]")
        print("bare adam opens the deterministic phone prompt; Adam itself performs no model inference")
        return 0
    print("[blocked] unknown Adam command; no model fallback is permitted", file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
