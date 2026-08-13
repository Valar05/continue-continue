#!/usr/bin/env python3
"""Adam: deterministic phone-facing command surface.

Adam does not perform model inference. It owns the prompt, mechanical shell
execution, working-directory state, Continue/Vlad invocation, and receipts.
Vlad remains the model-bearing helper.
"""

from __future__ import annotations

import json
import os
import pathlib
import shlex
import subprocess
import sys
import time

from adam_quotes import CATEGORIES, context_seed, format_quote, select_quote


def here() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def state_dir() -> pathlib.Path:
    root = pathlib.Path(os.path.expanduser(os.environ.get("ADAM_STATE_DIR", "~/.continue-continue/adam")))
    root.mkdir(parents=True, exist_ok=True)
    return root


def shell_state_path() -> pathlib.Path:
    return state_dir() / "shell-state.json"


def shell_receipt_path() -> pathlib.Path:
    return state_dir() / "shell-receipt.json"


def load_cwd() -> pathlib.Path:
    override = os.environ.get("ADAM_CWD")
    if override:
        candidate = pathlib.Path(os.path.expanduser(override))
        return candidate.resolve() if candidate.is_dir() else pathlib.Path.cwd()
    try:
        payload = json.loads(shell_state_path().read_text(encoding="utf-8"))
        candidate = pathlib.Path(str(payload.get("cwd") or ""))
        if candidate.is_dir():
            return candidate.resolve()
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return pathlib.Path.cwd().resolve()


def save_cwd(cwd: pathlib.Path) -> None:
    target = shell_state_path()
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps({"schema": "continue-continue.adam-shell-state.v1", "cwd": str(cwd)}, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


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


def codex_worker_command() -> list[str]:
    override = os.environ.get("ADAM_CODEX_WORKER_BIN")
    if override:
        return [override]
    return [sys.executable, str(here() / "codex_worker.py")]


def write_shell_receipt(command: str, cwd: pathlib.Path, returncode: int) -> None:
    target = shell_receipt_path()
    temp = target.with_suffix(".json.tmp")
    receipt = {
        "schema": "continue-continue.adam-shell-receipt.v1",
        "createdAt": int(time.time() * 1000),
        "command": command,
        "cwd": str(cwd),
        "returncode": returncode,
        "completed": returncode == 0,
        "modelUsed": False,
    }
    temp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)


def shell_command(command: str, cwd: pathlib.Path | None = None) -> int:
    shell = os.environ.get("ADAM_SHELL") or os.environ.get("SHELL") or "sh"
    workdir = (cwd or load_cwd()).resolve()
    completed = subprocess.run([shell, "-lc", command], cwd=workdir, check=False)
    write_shell_receipt(command, workdir, completed.returncode)
    return completed.returncode


def change_directory(argument: str, cwd: pathlib.Path) -> pathlib.Path:
    raw = argument.strip() or "~"
    candidate = pathlib.Path(os.path.expanduser(raw))
    if not candidate.is_absolute():
        candidate = cwd / candidate
    resolved = candidate.resolve()
    if not resolved.is_dir():
        raise NotADirectoryError(str(resolved))
    save_cwd(resolved)
    return resolved


def vlad(args: list[str]) -> int:
    return subprocess.run([*vlad_command(), *args], check=False).returncode


def codex_worker(args: list[str], cwd: pathlib.Path) -> int:
    command = codex_worker_command()
    if not args:
        return subprocess.run([*command, "doctor"], check=False).returncode
    if args[0] == "doctor":
        return subprocess.run([*command, *args], check=False).returncode
    if args[0] == "resume":
        if len(args) < 3:
            print("adam codex resume requires THREAD_ID and PROMPT", file=sys.stderr)
            return 2
        return subprocess.run([*command, "resume", args[1], " ".join(args[2:]), "--cwd", str(cwd)], check=False).returncode
    return subprocess.run([*command, "run", " ".join(args), "--cwd", str(cwd)], check=False).returncode


def quote_command(args: list[str], cwd: pathlib.Path | None = None) -> int:
    category: str | None = None
    seed: str | None = None
    json_output = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            json_output = True
            index += 1
            continue
        if token in {"--seed", "--category"}:
            if index + 1 >= len(args):
                print(f"adam quote {token} requires a value", file=sys.stderr)
                return 2
            value = args[index + 1]
            if token == "--seed":
                seed = value
            else:
                category = value
            index += 2
            continue
        print(f"[blocked] unknown adam quote option: {token}", file=sys.stderr)
        return 2
    selected_seed = seed or context_seed(cwd)
    try:
        quote = select_quote(selected_seed, category)
    except ValueError as exc:
        print(f"[blocked] {exc}; categories: {', '.join(sorted(CATEGORIES))}", file=sys.stderr)
        return 3
    if json_output:
        payload = quote.as_dict()
        payload.update(
            {
                "schema": "continue-continue.adam-quote.v1",
                "seed": selected_seed,
                "deterministic": True,
                "offline": True,
            }
        )
        print(json.dumps(payload, sort_keys=True))
    else:
        print(format_quote(quote))
    return 0


def repl() -> int:
    cwd = load_cwd()
    print("Adam local. Deterministic shell. /cd, /pwd, /quote, !CMD, /shell CMD, /codex, /code, /review, /doctor, /vlad, /quit.")
    print(format_quote(select_quote(context_seed(cwd))))
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
        if text == "/quote" or text.startswith("/quote "):
            quote_command(shlex.split(text[6:].strip()), cwd)
            continue
        if text == "/pwd":
            print(cwd)
            continue
        if text == "/cd" or text.startswith("/cd "):
            try:
                cwd = change_directory(text[3:].strip(), cwd)
                print(cwd)
            except OSError as exc:
                print(f"[blocked] cd: {exc}", file=sys.stderr)
            continue
        if text.startswith("!"):
            shell_command(text[1:].lstrip(), cwd)
            continue
        if text.startswith("/shell "):
            shell_command(text[7:].strip(), cwd)
            continue
        if text == "/codex" or text.startswith("/codex "):
            codex_worker(shlex.split(text[6:].strip()), cwd)
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
        print("[blocked] Unknown Adam input. Use an explicit deterministic command; no model fallback is permitted.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return repl()
    if argv[0] == "quote":
        return quote_command(argv[1:], load_cwd())
    if argv[0] == "doctor":
        return subprocess.run([*doctor_command(), *argv[1:]], check=False).returncode
    if argv[0] == "pwd":
        print(load_cwd())
        return 0
    if argv[0] == "cd":
        try:
            print(change_directory(" ".join(argv[1:]), load_cwd()))
            return 0
        except OSError as exc:
            print(f"[blocked] cd: {exc}", file=sys.stderr)
            return 3
    if argv[0] == "shell":
        if len(argv) < 2:
            print("adam shell requires a command", file=sys.stderr)
            return 2
        return shell_command(" ".join(argv[1:]), load_cwd())
    if argv[0] == "codex":
        return codex_worker(argv[1:], load_cwd())
    if argv[0] in {"code", "review", "status", "route", "phone", "observe", "home"}:
        return vlad(argv)
    if argv[0] in {"-h", "--help", "help"}:
        print("usage: adam [quote [--seed TEXT] [--category bible|literature|history] [--json]|doctor|pwd|cd [DIR]|shell CMD|codex [doctor|PROMPT|resume THREAD_ID PROMPT]|code PROMPT|review PROMPT|status|route ...|phone ...|observe|home]")
        print("bare adam opens the deterministic terminal; Adam itself performs no model inference")
        return 0
    print("[blocked] unknown Adam command; no model fallback is permitted", file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
