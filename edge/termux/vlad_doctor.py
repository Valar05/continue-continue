#!/usr/bin/env python3
"""Read-only readiness probe for the Continue Continue Vlad Termux edge."""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Mapping

SCHEMA = "continue-continue.vlad-doctor.v1"
DEFAULT_PHONE_ASK = "/data/data/com.termux/files/usr/local/bin/home-center-phone-ask"
DEFAULT_EDGE_BIN = "/data/data/com.termux/files/usr/local/bin/continue-continue-vlad"
DEFAULT_INTERNAL_EDGE_BIN = "/data/data/com.termux/files/usr/local/bin/continue-continue-vlad-edge"
DEFAULT_ROUTING_SHEET = "/data/data/com.termux/files/usr/etc/continue-continue/routes.csv"
DEFAULT_ALLOWED_BINS = "cn,git,ffmpeg,ffprobe,python,python3,node,npm,npx,rg,grep,find,ls,pwd,cat,mkdir,cp"
VALID_ROUTES = {"phone_hands", "shell", "delegate", "blocked", "passthrough"}
ROUTING_COLUMNS = {
    "priority",
    "enabled",
    "name",
    "domain",
    "contains_any",
    "contains_all",
    "route",
    "target_domain",
    "command",
    "phone_prompt",
    "reason",
}
KNOWN_REQUIREMENTS = {"continue", "phone_hands", "upstream", "qwen"}


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    required: bool
    detail: str


def _enabled(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "0") == "1"


def _probe_http(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code = int(getattr(response, "status", 200))
        return 200 <= code < 500, f"HTTP {code}"
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return False, f"unreachable: {exc}"


def _writable_directory(path: pathlib.Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="doctor-", dir=path, delete=True):
            pass
        return True, str(path)
    except OSError as exc:
        return False, f"not writable: {exc}"


def _executable(path: str) -> bool:
    target = pathlib.Path(path)
    return target.is_file() and os.access(target, os.X_OK)


def _command_path(command: str, env: Mapping[str, str]) -> str | None:
    expanded = os.path.expanduser(command)
    candidate = pathlib.Path(expanded)
    if candidate.is_absolute() or "/" in command:
        return str(candidate) if _executable(str(candidate)) else None
    return shutil.which(command, path=env.get("PATH"))


def _routing_sheet(path: str) -> tuple[bool, str]:
    target = pathlib.Path(path)
    if not target.is_file():
        return False, f"missing: {target}"
    try:
        with target.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            missing = sorted(ROUTING_COLUMNS - fields)
            if missing:
                return False, "missing columns: " + ",".join(missing)
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        return False, f"unreadable: {exc}"

    enabled_rows = [
        row
        for row in rows
        if str(row.get("enabled") or "").strip().lower()
        in {"1", "true", "yes", "on"}
    ]
    if not enabled_rows:
        return False, "routing sheet has no enabled rows"

    for index, row in enumerate(enabled_rows, start=1):
        name = str(row.get("name") or "").strip()
        if not name:
            return False, f"enabled row {index} has no name"
        try:
            int(str(row.get("priority") or ""))
        except ValueError:
            return False, f"rule {name} has invalid priority"
        route = str(row.get("route") or "").strip().lower()
        if route not in VALID_ROUTES:
            return False, f"rule {name} has invalid route: {route}"
        if route == "shell" and not str(row.get("command") or "").strip():
            return False, f"shell rule {name} has no command"

    return True, f"{target} ({len(enabled_rows)} enabled rows)"


def _parse_requirements(values: list[str], env: Mapping[str, str]) -> set[str]:
    required = set(values)
    required.update(filter(None, env.get("VLAD_DOCTOR_REQUIRE", "").split(",")))
    unknown = required - KNOWN_REQUIREMENTS
    if unknown:
        raise ValueError("unknown doctor requirement(s): " + ", ".join(sorted(unknown)))
    return required


def diagnose(
    env: Mapping[str, str] | None = None,
    requirements: set[str] | None = None,
) -> dict[str, object]:
    env = dict(os.environ if env is None else env)
    requirements = set() if requirements is None else set(requirements)
    checks: list[Check] = []

    python_ok = sys.version_info >= (3, 10)
    checks.append(
        Check(
            "python",
            python_ok,
            True,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )

    state_dir = pathlib.Path(
        env.get(
            "CONTINUE_CONTINUE_EDGE_DIR",
            pathlib.Path.home() / ".continue-continue" / "vlad",
        )
    )
    writable, detail = _writable_directory(state_dir)
    checks.append(Check("state_dir", writable, True, detail))

    edge_bin = env.get("VLAD_EDGE_BIN", DEFAULT_EDGE_BIN)
    checks.append(Check("edge_binary", _executable(edge_bin), True, edge_bin))

    internal_edge = env.get("VLAD_EDGE_INTERNAL", DEFAULT_INTERNAL_EDGE_BIN)
    checks.append(
        Check("internal_edge_binary", _executable(internal_edge), True, internal_edge)
    )

    sheet = env.get("VLAD_ROUTING_SHEET", DEFAULT_ROUTING_SHEET)
    sheet_ok, sheet_detail = _routing_sheet(sheet)
    checks.append(Check("routing_sheet", sheet_ok, True, sheet_detail))

    continue_required = "continue" in requirements
    cn_command = env.get("VLAD_CN_BIN", "cn")
    cn_path = _command_path(cn_command, env)
    cn_name = pathlib.Path(cn_command).name
    shell_policy = set(
        filter(None, env.get("VLAD_ALLOWED_BINS", DEFAULT_ALLOWED_BINS).split(","))
    )
    continue_gate_ok = _enabled(env, "VLAD_ALLOW_LOCAL_EXEC")
    continue_policy_ok = cn_name in shell_policy
    checks.append(
        Check(
            "continue_binary",
            bool(cn_path),
            continue_required,
            cn_path or f"not found: {cn_command}",
        )
    )
    checks.append(
        Check(
            "continue_permission",
            continue_gate_ok,
            continue_required,
            "VLAD_ALLOW_LOCAL_EXEC=" + ("1" if continue_gate_ok else "0"),
        )
    )
    checks.append(
        Check(
            "continue_policy",
            continue_policy_ok,
            continue_required,
            f"{cn_name} " + ("allowed" if continue_policy_ok else "excluded") + " by VLAD_ALLOWED_BINS",
        )
    )

    phone_required = "phone_hands" in requirements
    phone_bin = env.get("PHONE_ASK_BIN", DEFAULT_PHONE_ASK)
    phone_bin_ok = _executable(phone_bin)
    phone_gate_ok = _enabled(env, "VLAD_ALLOW_PHONE_HANDS")
    checks.append(Check("phone_hands_binary", phone_bin_ok, phone_required, phone_bin))
    checks.append(
        Check(
            "phone_hands_permission",
            phone_gate_ok,
            phone_required,
            "VLAD_ALLOW_PHONE_HANDS=" + ("1" if phone_gate_ok else "0"),
        )
    )

    upstream_required = "upstream" in requirements
    upstream = env.get("CONTINUE_CONTINUE_UPSTREAM_URL", "").rstrip("/")
    if upstream:
        upstream_ok, upstream_detail = _probe_http(
            upstream + "/automation/capabilities"
        )
    else:
        upstream_ok, upstream_detail = (
            False,
            "CONTINUE_CONTINUE_UPSTREAM_URL is not configured",
        )
    checks.append(Check("upstream", upstream_ok, upstream_required, upstream_detail))

    qwen_required = "qwen" in requirements
    qwen = env.get("QWEN_BASE_URL", "").rstrip("/")
    if qwen:
        qwen_ok, qwen_detail = _probe_http(qwen + "/models")
    else:
        qwen_ok, qwen_detail = False, "QWEN_BASE_URL is not configured"
    checks.append(Check("qwen", qwen_ok, qwen_required, qwen_detail))

    for binary in ("git", "python3", "ffmpeg", "ffprobe", "rg"):
        path = shutil.which(binary, path=env.get("PATH"))
        checks.append(Check(f"tool:{binary}", bool(path), False, path or "not found"))

    required_failures = [
        check.name for check in checks if check.required and not check.ok
    ]
    optional_failures = [
        check.name for check in checks if not check.required and not check.ok
    ]
    return {
        "schema": SCHEMA,
        "ready": not required_failures,
        "required": sorted(requirements),
        "requiredFailures": required_failures,
        "optionalFailures": optional_failures,
        "checks": [asdict(check) for check in checks],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Vlad edge readiness probe")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        choices=sorted(KNOWN_REQUIREMENTS),
        help="Capability that must be ready; may be repeated.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)
    try:
        requirements = _parse_requirements(args.require, os.environ)
    except ValueError as exc:
        print(json.dumps({"schema": SCHEMA, "ready": False, "error": str(exc)}))
        return 2
    report = diagnose(requirements=requirements)
    print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
