#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 The feedBack plugin-spec authors
"""Assemble the MkDocs `docs/` tree from the canonical sources.

The spec prose lives in `spec/`, the changelog at the repo root, and the schema in
`schemas/` — those stay the single source of truth. This script copies them into
`docs/` (the MkDocs `docs_dir`) and rewrites the few repo-relative links that would
otherwise break once rendered at the site root.

Generated outputs (`docs/plugin-spec-v1.md`, `docs/best-practices.md`,
`docs/changelog.md`, `docs/schemas/`) are gitignored; `docs/index.md` and `mkdocs.yml`
are committed. Run by .github/workflows/pages.yml and reproducible locally before
`mkdocs build`.

    python tools/gen_docs.py && mkdocs build
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
BLOB = "https://github.com/got-feedback/feedBack-plugin-spec/blob/main"

# Repo-relative links -> site-relative (or absolute GitHub) equivalents. Order matters:
# longer/more-specific prefixes before the shorter ones. `plugin-spec-v1.md`,
# `best-practices.md`, and intra-doc `#anchor` links already resolve at the site root
# and need no rewrite; only links that climb out of `spec/` (../) are repointed.
LINK_REWRITES = {
    # `../`-relative links (from files under spec/).
    "(../CONTRIBUTING.md": f"({BLOB}/CONTRIBUTING.md",
    "(../GOVERNANCE.md": f"({BLOB}/GOVERNANCE.md",
    "(../examples/": f"({BLOB}/examples/",
    "(../schemas/": "(schemas/",
    "(../CHANGELOG.md": "(changelog.md",
    "(../LICENSE": f"({BLOB}/LICENSE",
    # Repo-root-relative links (from CHANGELOG.md, copied to docs/changelog.md).
    "(spec/plugin-spec-v1.md": "(plugin-spec-v1.md",
    "(spec/best-practices.md": "(best-practices.md",
    "(examples/": f"({BLOB}/examples/",
    "(tools/": f"({BLOB}/tools/",
    "(LICENSE)": f"({BLOB}/LICENSE)",
}


def _copy_md(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    for old, new in LINK_REWRITES.items():
        text = text.replace(old, new)
    dest.write_text(text, encoding="utf-8")


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    _copy_md(ROOT / "spec" / "plugin-spec-v1.md", DOCS / "plugin-spec-v1.md")
    _copy_md(ROOT / "spec" / "best-practices.md", DOCS / "best-practices.md")
    _copy_md(ROOT / "CHANGELOG.md", DOCS / "changelog.md")

    schemas_out = DOCS / "schemas"
    if schemas_out.exists():
        shutil.rmtree(schemas_out)
    schemas_out.mkdir()
    for schema in sorted((ROOT / "schemas").glob("*.json")):
        shutil.copy2(schema, schemas_out / schema.name)

    print(f"docs tree assembled in {DOCS}")


if __name__ == "__main__":
    main()
