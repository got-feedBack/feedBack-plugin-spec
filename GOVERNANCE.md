# Governance

This document describes how the feedBack plugin specification is maintained and how new versions
are decided and cut. It is intentionally lightweight; the goal is a stable, predictable format,
not bureaucracy.

## Roles

- **Maintainers** — the people with merge rights on this repository. They review proposals,
  steward releases, and keep the spec, schema, examples, and validator consistent with one
  another.
- **Contributors** — anyone who opens an issue or pull request. No special status is required to
  propose a change.

## How decisions are made

Changes are proposed and discussed in the open as **Plugin Spec Enhancement Proposals** — see
[CONTRIBUTING.md](CONTRIBUTING.md). The working model is **rough consensus**:

- A proposal is accepted when it has a clear design, no unresolved objections from maintainers, and
  the corresponding spec + schema + example + changelog changes are ready.
- Editorial changes (typos, clarifications that do not change conformance) may be merged by a
  maintainer without a proposal.
- When consensus cannot be reached, maintainers make the final call, and the reasoning is recorded
  in the issue or PR.

## Compatibility is the prime directive

The format exists so that plugins and the Host can rely on a stable contract. Every decision is
weighed against that. In practice:

- **Prefer additive change.** New capability should arrive as a new *optional* manifest key that an
  older Host can ignore (a MINOR bump).
- **Deprecate, don't break.** When a key must change, the preferred path is: add the new key, mark
  the old one deprecated in the spec, and keep honouring it for at least one MINOR release before
  any MAJOR release removes it.
- **MAJOR bumps are rare and deliberate.** A backward-incompatible change to the manifest requires
  a new manifest major version and a new spec document (`spec/plugin-spec-v2.md`) with an explicit
  migration note, not an in-place edit.

## Cutting a release

A maintainer cuts a specification release by:

1. Ensuring the spec, `schemas/`, `examples/`, and `tools/validate.py` are mutually consistent and
   CI is green.
2. Moving the `[Unreleased]` entries in [CHANGELOG.md](CHANGELOG.md) under a new version heading
   with the date.
3. Updating the version in the spec header and the README table (the `tools/check_versions.py`
   guard enforces that these agree).
4. Merging to `main`, which cuts the `vMAJOR.MINOR.PATCH` tag and GitHub Release automatically.

## Relationship to implementations

This repository defines the plugin format only. The feedBack Host (server + desktop app) and the
individual plugins are separate efforts that track this spec as a dependency; they do not drive it.
A change is not part of the format until it lands here.
