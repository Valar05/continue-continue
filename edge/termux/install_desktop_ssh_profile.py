#!/usr/bin/env python3
"""Install a normal OpenSSH desktop profile for Termux.

No credentials or private keys are generated or copied. The result is a standard
`ssh desktop` alias that remains usable without Adam, Continue, or a model.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

ALIAS_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def ssh_root(env: dict[str, str] | None = None) -> pathlib.Path:
    env = dict(os.environ if env is None else env)
    return pathlib.Path(os.path.expanduser(env.get("ADAM_SSH_DIR", "~/.ssh")))


def validate_alias(value: str) -> str:
    alias = value.strip()
    if not ALIAS_RE.fullmatch(alias):
        raise ValueError("SSH alias must use only letters, numbers, _, ., or -")
    return alias


def render_profile(alias: str, host: str, user: str = "", port: int = 22, identity: str = "") -> str:
    alias = validate_alias(alias)
    host = host.strip()
    if not host or any(char.isspace() for char in host):
        raise ValueError("desktop SSH host is required and cannot contain whitespace")
    if not (1 <= int(port) <= 65535):
        raise ValueError("SSH port must be between 1 and 65535")
    lines = [
        "# Managed by Continue Continue. No secrets are stored here.",
        f"Host {alias}",
        f"    HostName {host}",
        f"    Port {int(port)}",
        "    ServerAliveInterval 30",
        "    ServerAliveCountMax 3",
        "    TCPKeepAlive yes",
    ]
    if user.strip():
        lines.append(f"    User {user.strip()}")
    if identity.strip():
        expanded = pathlib.Path(os.path.expanduser(identity.strip()))
        lines.append(f"    IdentityFile {expanded}")
        lines.append("    IdentitiesOnly yes")
    return "\n".join(lines) + "\n"


def ensure_include(config: pathlib.Path) -> None:
    include_line = "Include config.d/*"
    existing = config.read_text(encoding="utf-8") if config.exists() else ""
    if any(line.strip() == include_line for line in existing.splitlines()):
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    config.write_text(existing + prefix + include_line + "\n", encoding="utf-8")


def install(alias: str, host: str, user: str = "", port: int = 22, identity: str = "", env: dict[str, str] | None = None) -> dict[str, object]:
    root = ssh_root(env)
    config_d = root / "config.d"
    root.mkdir(parents=True, exist_ok=True)
    config_d.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
        config_d.chmod(0o700)
    except OSError:
        pass

    alias = validate_alias(alias)
    target = config_d / f"continue-continue-{alias}.conf"
    text = render_profile(alias, host, user=user, port=port, identity=identity)
    temp = target.with_suffix(".conf.tmp")
    temp.write_text(text, encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(target)
    ensure_include(root / "config")

    receipt = {
        "schema": "continue-continue.desktop-ssh-profile.v1",
        "createdAt": int(time.time() * 1000),
        "alias": alias,
        "host": host,
        "user": user or None,
        "port": int(port),
        "identityConfigured": bool(identity.strip()),
        "profile": str(target),
        "config": str(root / "config"),
        "command": f"ssh {alias}",
        "secretsStored": False,
    }
    receipt_path = config_d / f"continue-continue-{alias}.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    try:
        receipt_path.chmod(0o600)
    except OSError:
        pass
    receipt["receiptPath"] = str(receipt_path)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adam-ssh-profile", description="Install a normal Termux OpenSSH desktop alias.")
    parser.add_argument("--alias", default=os.environ.get("DESKTOP_SSH_ALIAS", "desktop"))
    parser.add_argument("--host", default=os.environ.get("DESKTOP_SSH_HOST", "THECAULDRON"))
    parser.add_argument("--user", default=os.environ.get("DESKTOP_SSH_USER", ""))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DESKTOP_SSH_PORT", "22")))
    parser.add_argument("--identity", default=os.environ.get("DESKTOP_SSH_IDENTITY", ""))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = install(args.alias, args.host, user=args.user, port=args.port, identity=args.identity)
    except (OSError, ValueError) as exc:
        print(f"[blocked] {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        print(f"[installed] {receipt['command']} -> {receipt['host']}:{receipt['port']}")
        print(f"profile={receipt['profile']}")
        print(f"receipt={receipt['receiptPath']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
