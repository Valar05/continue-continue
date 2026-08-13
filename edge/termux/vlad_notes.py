#!/usr/bin/env python3
"""Deterministic, local-only context-pack tools for Vlad.

This is evidence retrieval, not memory, inference, or shell authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from typing import Any

SCHEMA = "continue-continue.vlad-context-pack.v1"
RECEIPT_SCHEMA = "continue-continue.vlad-notes-receipt.v1"
DEFAULT_ROOT = "~/storage/shared/GodotProjects"
DEFAULT_STATE = "~/.continue-continue/vlad-notes"
ALLOWED_ROOT_FILES = {"AGENTS.md", "MEMORY.md", "SKILLS.md", "state.md"}
ALLOWED_DIRS = ("docs/", ".continue/rules/", ".continue/checks/")
ALLOWED_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}
SUSPICIOUS_NAME = re.compile(r"(secret|credential|token|cookie|auth|private|\.env|\.pem|\.key)", re.I)
SECRET_ASSIGNMENT = re.compile(
    r"(?im)^([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|COOKIE|API_KEY|PRIVATE_KEY)[A-Z0-9_]*\s*[:=]\s*).+$"
)
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024
MAX_FILES = 2000


def state_dir() -> pathlib.Path:
    path = pathlib.Path(os.path.expanduser(os.environ.get("VLAD_NOTES_STATE_DIR", DEFAULT_STATE)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def pack_path() -> pathlib.Path:
    return state_dir() / "context-pack.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def approved(path: pathlib.Path, root: pathlib.Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if path.is_symlink() or SUSPICIOUS_NAME.search(rel):
        return False
    if rel in ALLOWED_ROOT_FILES:
        return True
    return rel.endswith(tuple(ALLOWED_SUFFIXES)) and rel.startswith(ALLOWED_DIRS)


def redact(text: str) -> str:
    return SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", text)


def compile_pack(root_arg: str | None) -> dict[str, Any]:
    root = pathlib.Path(os.path.expanduser(root_arg or os.environ.get("VLAD_NOTES_ROOT", DEFAULT_ROOT))).resolve()
    if not root.is_dir():
        raise RuntimeError(f"approved root is unavailable: {root}")
    sources: list[dict[str, Any]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if len(sources) >= MAX_FILES:
            break
        if not path.is_file() or not approved(path, root):
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            continue
        raw = path.read_bytes()
        try:
            text = redact(raw.decode("utf-8"))
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(root).as_posix()
        sources.append(
            {
                "path": relative,
                "sha256": digest(raw),
                "bytes": size,
                "text": text,
            }
        )
        total += size
    payload = {
        "schema": SCHEMA,
        "generatedAt": int(os.environ.get("SOURCE_DATE_EPOCH", "0")) * 1000,
        "root": str(root),
        "sourceCount": len(sources),
        "sourceBytes": total,
        "sources": sources,
    }
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    atomic_write(pack_path(), encoded)
    atomic_write(pack_path().with_suffix(".sha256"), (digest(encoded) + "\n").encode())
    return {**payload, "sources": None, "packSha256": digest(encoded), "path": str(pack_path())}


def load_pack() -> tuple[dict[str, Any], str]:
    raw = pack_path().read_bytes()
    expected = pack_path().with_suffix(".sha256").read_text(encoding="utf-8").strip()
    actual = digest(raw)
    if expected != actual:
        raise RuntimeError("context pack hash mismatch")
    payload = json.loads(raw)
    if payload.get("schema") != SCHEMA:
        raise RuntimeError("unsupported context pack schema")
    return payload, actual


def status() -> dict[str, Any]:
    try:
        pack, pack_hash = load_pack()
        return {
            "schema": SCHEMA,
            "ready": True,
            "packSha256": pack_hash,
            "generatedAt": pack["generatedAt"],
            "sourceCount": pack["sourceCount"],
            "sourceBytes": pack["sourceBytes"],
            "path": str(pack_path()),
            "modelUsed": False,
        }
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        return {"schema": SCHEMA, "ready": False, "blocked": str(exc), "modelUsed": False}


def query(terms: list[str]) -> dict[str, Any]:
    pack, pack_hash = load_pack()
    needles = [term.casefold() for term in terms if term.strip()]
    if not needles:
        raise ValueError("query requires non-empty terms")
    matches = []
    for source in pack["sources"]:
        body = source["text"].casefold()
        score = sum(body.count(needle) for needle in needles)
        if score:
            lines = [
                line.strip()
                for line in source["text"].splitlines()
                if any(needle in line.casefold() for needle in needles)
            ][:8]
            matches.append({"path": source["path"], "score": score, "lines": lines})
    matches.sort(key=lambda item: (-item["score"], item["path"]))
    return {
        "schema": SCHEMA,
        "packSha256": pack_hash,
        "query": terms,
        "matches": matches[:20],
        "modelUsed": False,
    }


def next_action() -> dict[str, Any]:
    pack, pack_hash = load_pack()
    candidates = []
    marker = re.compile(r"(?i)\b(remaining gate|next action|continue_required|blocked)\b")
    for source in pack["sources"]:
        for index, line in enumerate(source["text"].splitlines(), start=1):
            if marker.search(line):
                candidates.append({"path": source["path"], "line": index, "text": line.strip()})
    return {
        "schema": SCHEMA,
        "packSha256": pack_hash,
        "candidates": candidates[:50],
        "selected": candidates[0] if candidates else None,
        "modelUsed": False,
    }


def append_receipt(decision: str, source_ids: list[str]) -> dict[str, Any]:
    _, pack_hash = load_pack()
    ledger = state_dir() / "receipts.jsonl"
    previous = ""
    if ledger.exists():
        lines = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            previous = json.loads(lines[-1])["receiptSha256"]
    body = {
        "schema": RECEIPT_SCHEMA,
        "createdAt": int(time.time() * 1000),
        "decision": decision,
        "packSha256": pack_hash,
        "sourceIds": source_ids,
        "previousReceiptSha256": previous,
        "modelUsed": False,
    }
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receiptSha256"] = digest(canonical.encode())
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vlad-notes")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("root", nargs="?")
    query_parser = sub.add_parser("query")
    query_parser.add_argument("terms", nargs="+")
    sub.add_parser("next")
    receipt_parser = sub.add_parser("receipt")
    receipt_parser.add_argument("decision")
    receipt_parser.add_argument("source_ids", nargs="*")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = status()
            print(json.dumps(result, indent=2))
            return 0 if result["ready"] else 3
        if args.command == "compile":
            result = compile_pack(args.root)
        elif args.command == "query":
            result = query(args.terms)
        elif args.command == "next":
            result = next_action()
        else:
            result = append_receipt(args.decision, args.source_ids)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"blocked": str(exc), "modelUsed": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
