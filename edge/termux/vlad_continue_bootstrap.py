#!/usr/bin/env python3
"""Bootstrap the minimum local Continue coder for Vlad/Termux.

This is intentionally stdlib-only. It discovers models from a local Ollama
server, selects the smallest useful coding-biased model unless explicitly
pinned, and writes the smallest Continue config needed for chat/edit/apply.
It never downloads a model and never overwrites a non-empty user config without
--force.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Mapping

SCHEMA = "continue-continue.vlad-bootstrap.v1"
DEFAULT_OLLAMA = "http://127.0.0.1:11434"


def continue_dir(env: Mapping[str, str]) -> pathlib.Path:
    configured = env.get("CONTINUE_GLOBAL_DIR", "").strip()
    if configured:
        path = pathlib.Path(os.path.expanduser(configured))
        return path if path.is_absolute() else pathlib.Path.cwd() / path
    return pathlib.Path.home() / ".continue"


def config_path(env: Mapping[str, str]) -> pathlib.Path:
    return continue_dir(env) / "config.yaml"


def ollama_base(env: Mapping[str, str]) -> str:
    raw = (env.get("VLAD_OLLAMA_URL") or env.get("OLLAMA_HOST") or DEFAULT_OLLAMA).strip()
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw
    return raw.rstrip("/")


def list_models(env: Mapping[str, str], timeout: float = 2.0) -> list[dict[str, Any]]:
    url = ollama_base(env) + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama is unreachable at {url}: {exc}") from exc
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError(f"Ollama returned no model list from {url}")
    return [item for item in models if isinstance(item, dict) and str(item.get("name") or "").strip()]


def _model_size(item: Mapping[str, Any]) -> int:
    try:
        return int(item.get("size") or 0)
    except (TypeError, ValueError):
        return 0


def choose_model(models: list[dict[str, Any]], requested: str | None = None) -> str:
    names = [str(item.get("name") or "").strip() for item in models]
    if requested:
        requested = requested.strip()
        if requested not in names:
            raise RuntimeError(
                f"Requested Ollama model {requested!r} is not installed. Installed: "
                + (", ".join(names) if names else "none")
            )
        return requested
    if not models:
        raise RuntimeError(
            "Ollama has no installed models. Vlad will not download one implicitly; install/pull a small coding model, then rerun bootstrap."
        )

    def rank(item: Mapping[str, Any]) -> tuple[int, int, str]:
        name = str(item.get("name") or "").lower()
        # Prefer Qwen coder, then any coder, then Qwen, then any installed model.
        if "qwen" in name and "coder" in name:
            family = 0
        elif "coder" in name or "code" in name:
            family = 1
        elif "qwen" in name:
            family = 2
        else:
            family = 3
        size = _model_size(item)
        # Unknown size sorts after known sizes within a family.
        return family, size if size > 0 else sys.maxsize, name

    return str(min(models, key=rank).get("name"))


def _yaml_quote(value: str) -> str:
    # JSON strings are valid YAML scalar strings and avoid hand-rolled escaping.
    return json.dumps(value, ensure_ascii=False)


def render_config(model: str, base_url: str) -> str:
    lines = [
        "# Managed by `vlad bootstrap` for the minimum local coding path.",
        "name: Vlad Local",
        'version: "1.0.0"',
        'schema: "v1"',
        "models:",
        f"  - name: {_yaml_quote('Vlad ' + model)}",
        "    provider: ollama",
        f"    model: {_yaml_quote(model)}",
    ]
    if base_url.rstrip("/") != DEFAULT_OLLAMA:
        lines.append(f"    apiBase: {_yaml_quote(base_url.rstrip('/'))}")
    lines.extend(
        [
            "    roles:",
            "      - chat",
            "      - edit",
            "      - apply",
            "",
        ]
    )
    return "\n".join(lines)


def config_is_replaceable(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if "Managed by `vlad bootstrap`" in text:
        return True
    compact = "".join(stripped.split())
    # Continue's generated default is name/version/schema plus an empty models list.
    return "models:[]" in compact and "provider:" not in compact


def install_config(
    env: Mapping[str, str], model: str, *, force: bool = False
) -> tuple[pathlib.Path, pathlib.Path | None]:
    target = config_path(env)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    backup: pathlib.Path | None = None
    if existing and not config_is_replaceable(existing):
        if not force:
            raise RuntimeError(
                f"Refusing to replace non-empty Continue config at {target}. Re-run with --force to preserve it as a backup and install Vlad local config."
            )
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(f"config.yaml.vlad-backup-{stamp}")
        shutil.copy2(target, backup)
    target.write_text(render_config(model, ollama_base(env)), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return target, backup


def bootstrap(
    env: Mapping[str, str] | None = None,
    *,
    requested_model: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    models = list_models(env)
    requested = requested_model or env.get("VLAD_OLLAMA_MODEL")
    model = choose_model(models, requested)
    target, backup = install_config(env, model, force=force)
    return {
        "schema": SCHEMA,
        "status": "configured",
        "model": model,
        "ollama": ollama_base(env),
        "config": str(target),
        "backup": str(backup) if backup else None,
        "installedModels": [str(item.get("name")) for item in models],
        "next": "vlad doctor --require continue",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vlad bootstrap",
        description="Configure the minimum local Ollama-backed Continue coder for Vlad.",
    )
    parser.add_argument("--model", help="require this already-installed Ollama model")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace a non-empty Continue config after preserving a timestamped backup",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        result = bootstrap(requested_model=args.model, force=args.force)
    except RuntimeError as exc:
        payload = {"schema": SCHEMA, "status": "blocked", "error": str(exc)}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"[blocked] {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"[configured] model={result['model']}")
        print(f"config={result['config']}")
        if result["backup"]:
            print(f"backup={result['backup']}")
        print(result["next"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
