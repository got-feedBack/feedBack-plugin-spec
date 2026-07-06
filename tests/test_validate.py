# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 The feedBack plugin-spec authors
"""Unit + end-to-end tests for the reference plugin validator."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import validate  # noqa: E402


@pytest.fixture(scope="module")
def validator():
    return validate._load_schema()


def _write_plugin(tmp_path: Path, dirname: str, manifest: dict, files=()) -> Path:
    plugin_dir = tmp_path / dirname
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    for rel in files:
        f = plugin_dir / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("", encoding="utf-8")
    return plugin_dir


def test_bundled_examples_are_valid(validator):
    for name in ("minimal-plugin", "full-plugin"):
        errors = validate.validate_plugin(ROOT / "examples" / name, validator)
        assert errors == [], f"{name}: {errors}"


def test_missing_manifest(tmp_path, validator):
    (tmp_path / "empty").mkdir()
    errors = validate.validate_plugin(tmp_path / "empty", validator)
    assert any("no plugin.json" in e for e in errors)


def test_missing_id_fails_schema(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "noid", {"name": "No Id"})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("schema" in e and "id" in e for e in errors)


def test_dir_name_must_match_id(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "wrong-name", {"id": "right-name"})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("does not match manifest id" in e for e in errors)


def test_referenced_file_must_exist(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "p", {"id": "p", "script": "screen.js"})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("referenced file not found: screen.js" in e for e in errors)


def test_referenced_file_present_ok(tmp_path, validator):
    plugin_dir = _write_plugin(
        tmp_path, "p", {"id": "p", "script": "screen.js"}, files=["screen.js"]
    )
    assert validate.validate_plugin(plugin_dir, validator) == []


def test_settings_html_reference_checked(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "p", {"id": "p", "settings": {"html": "settings.html"}})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("referenced file not found: settings.html" in e for e in errors)


def test_bad_id_pattern_fails_schema(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "Bad_Id", {"id": "Bad_Id"})
    errors = validate.validate_plugin(plugin_dir, validator)
    # Uppercase violates the id pattern.
    assert any("schema" in e for e in errors)


def test_absolute_referenced_path_rejected(tmp_path, validator):
    plugin_dir = _write_plugin(tmp_path, "p", {"id": "p", "script": "/etc/passwd"})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("must be relative" in e for e in errors)


def test_traversal_referenced_path_rejected(tmp_path, validator):
    # A file that exists just outside the plugin dir must not satisfy the reference.
    (tmp_path / "secret.txt").write_text("", encoding="utf-8")
    plugin_dir = _write_plugin(tmp_path, "p", {"id": "p", "script": "../secret.txt"})
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("escapes the plugin directory" in e for e in errors)


def test_invalid_json(tmp_path, validator):
    plugin_dir = tmp_path / "p"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("{not json", encoding="utf-8")
    errors = validate.validate_plugin(plugin_dir, validator)
    assert any("not valid JSON" in e for e in errors)
