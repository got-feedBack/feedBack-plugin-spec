#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 The feedBack plugin-spec authors
"""Reference validator for feedBack plugins.

Given one or more plugin directories, this checks each against the specification
(spec/plugin-spec-v1.md) and the manifest schema (schemas/plugin.schema.json):

  1. plugin.json exists and is valid JSON.
  2. plugin.json validates against schemas/plugin.schema.json (Draft 2020-12).
  3. The directory name equals the manifest `id`         (spec §5.2).
  4. Every file the manifest references actually exists   (spec §3, §4).

It doubles as the CI gate (see .github/workflows/validate.yml) and as a minimal
reference implementation of the discovery contract.

    pip install jsonschema
    python tools/validate.py examples/minimal-plugin examples/full-plugin
    python tools/validate.py path/to/my-plugin

Exit status is 0 when every given plugin is valid, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "plugin.schema.json"

# Manifest keys whose value is a single relative path to a file that must exist.
_FILE_PATH_KEYS = ("script", "screen", "styles", "routes", "tour")


class SchemaError(Exception):
    """The manifest schema itself is missing, unreadable, or invalid."""


def _load_schema() -> Draft202012Validator:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SchemaError(f"cannot read schema {SCHEMA_PATH}: {exc}") from exc
    except ValueError as exc:
        raise SchemaError(f"schema {SCHEMA_PATH} is not valid JSON: {exc}") from exc
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema.SchemaError and friends
        raise SchemaError(f"schema {SCHEMA_PATH} is not a valid JSON Schema: {exc}") from exc
    return Draft202012Validator(schema)


def _referenced_files(manifest: dict) -> list[str]:
    """Relative paths the manifest points at and that must exist on disk."""
    refs: list[str] = [manifest[k] for k in _FILE_PATH_KEYS if isinstance(manifest.get(k), str)]
    settings = manifest.get("settings")
    if isinstance(settings, dict) and isinstance(settings.get("html"), str):
        refs.append(settings["html"])
    return refs


def validate_plugin(plugin_dir: Path, validator: Draft202012Validator) -> list[str]:
    """Return a list of human-readable errors for one plugin dir (empty == valid)."""
    errors: list[str] = []

    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        return [f"no plugin.json in {plugin_dir}"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"plugin.json is not valid JSON: {exc}"]
    except OSError as exc:
        return [f"cannot read plugin.json: {exc}"]

    if not isinstance(manifest, dict):
        return ["plugin.json must contain a JSON object"]

    # 2. Schema.
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"schema: {loc}: {err.message}")

    # 3. Directory name == id (only meaningful once id is a valid string).
    plugin_id = manifest.get("id")
    if isinstance(plugin_id, str) and plugin_id and plugin_dir.name != plugin_id:
        errors.append(
            f"directory name {plugin_dir.name!r} does not match manifest id {plugin_id!r} "
            f"(spec §5.2)"
        )

    # 4. Every referenced file exists AND stays inside the plugin directory.
    #    The spec (§4.3) defines these as paths relative to the plugin directory; an
    #    absolute path or a `..` that climbs out (including via a symlink) escapes the
    #    plugin and is rejected rather than resolved.
    try:
        base = plugin_dir.resolve(strict=False)
    except OSError as exc:
        return errors + [f"cannot resolve plugin directory: {exc}"]
    for rel in _referenced_files(manifest):
        # Treat POSIX- and Windows-rooted paths as absolute regardless of the host OS,
        # so `/etc/passwd` is rejected the same way on Linux and Windows (where
        # Path.is_absolute() is False for a driveless root).
        if Path(rel).is_absolute() or rel.startswith(("/", "\\")):
            errors.append(f"referenced path must be relative, not absolute: {rel}")
            continue
        target = (plugin_dir / rel).resolve(strict=False)
        if base != target and base not in target.parents:
            errors.append(f"referenced path escapes the plugin directory: {rel}")
            continue
        if not target.is_file():
            errors.append(f"referenced file not found: {rel}")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate.py PLUGIN_DIR [PLUGIN_DIR ...]", file=sys.stderr)
        return 2

    try:
        validator = _load_schema()
    except SchemaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    ok = True
    for arg in argv[1:]:
        plugin_dir = Path(arg)
        errors = validate_plugin(plugin_dir, validator)
        if errors:
            ok = False
            print(f"FAIL {plugin_dir}")
            for e in errors:
                print(f"       - {e}")
        else:
            print(f"ok   {plugin_dir}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
