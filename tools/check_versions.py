#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 The feedBack plugin-spec authors
"""Guard: every place the *current* specification version is written must agree.

A version bump is a few hand-edits across several files; this guard fails CI
(pre-merge) if any one of them is missed, keeping the published version, the docs,
and the release-on-merge workflow in lockstep. It checks all of:

  - spec/plugin-spec-v1.md   header "- **Specification version:** X"
  - README.md                the version table row "**Specification version** | X"
  - CHANGELOG.md             the newest released `## [X.Y.Z]` section

(The example plugins carry their own independent `version`; they deliberately do
not track the specification version and are not checked here.)

    python tools/check_versions.py            # exit 0 if consistent, 1 otherwise
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changelog_extract import latest_version  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

_SPEC_HEADER_RE = re.compile(r"^- \*\*Specification version:\*\* (\d+\.\d+\.\d+)", re.MULTILINE)
_README_TABLE_RE = re.compile(r"\*\*Specification version\*\*\s*\|\s*(\d+\.\d+\.\d+)")


def _read(rel: str) -> str | None:
    try:
        return (ROOT / rel).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {rel}: {exc}", file=sys.stderr)
        return None


def _one(pattern: re.Pattern[str], text: str, label: str) -> str | None:
    m = pattern.search(text)
    if not m:
        print(f"error: could not find the version in {label}", file=sys.stderr)
        return None
    return m.group(1)


def collect() -> dict[str, str | None]:
    found: dict[str, str | None] = {}

    spec_text = _read("spec/plugin-spec-v1.md")
    readme_text = _read("README.md")
    changelog_text = _read("CHANGELOG.md")
    if spec_text is None or readme_text is None or changelog_text is None:
        found["<unreadable file>"] = None
        return found

    found["spec header"] = _one(_SPEC_HEADER_RE, spec_text, "spec header")
    found["README table"] = _one(_README_TABLE_RE, readme_text, "README version table")

    changelog = latest_version(changelog_text)
    if changelog is None:
        print("error: no released version section in CHANGELOG.md", file=sys.stderr)
    found["CHANGELOG"] = changelog

    return found


def main() -> int:
    found = collect()
    if None in found.values():
        return 1
    if len(set(found.values())) != 1:
        print("error: version mismatch across sources:", file=sys.stderr)
        for label, ver in found.items():
            print(f"  {label:20} {ver}", file=sys.stderr)
        return 1
    print(f"versions consistent: {found['spec header']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
