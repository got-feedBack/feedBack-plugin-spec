# Changelog

All notable changes to the feedBack plugin specification are documented here.

This repository is licensed under [AGPL-3.0-only](LICENSE). This file follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the specification is versioned per
[Semantic Versioning](https://semver.org/) — see [spec §9](spec/plugin-spec-v1.md#9-versioning-and-compatibility)
for how the document, manifest, and per-plugin versions relate.

## [Unreleased]

### Changed
- §8 (Capabilities) and `schemas/plugin.schema.json` now document the real capability-declaration
  vocabulary, ground-truthed against every bundled plugin: the domain keys and fields are an
  **open set** defined by the declared standard (e.g. `capability-pipelines.v1`), and a declaration
  may carry `operations` / `requests` (alongside `commands`), `emits` / `observes` (alongside
  `events`), plus `kind` and `description`. The `compatibility` field is no longer a hard schema
  enum (its values are an open set); the observed values are documented instead. Purely additive
  and clarifying — every existing manifest still validates.
- §6 (Client surface) rewritten to document the client screen contract, ground-truthed against the
  Host. Adds the **mount lifecycle** (§6.1 — Host-created container, `screen`-sourced markup,
  self-executing `script` with **no Host-invoked entry point**, and a normative **idempotent
  re-hydration MUST**), **screen activation/visibility** (§6.2), and a description of the
  **Host-provided, Host-versioned runtime surface** (§6.3 — event bus, contribution registries, and
  the forward-stable capability control plane; raw window globals documented as supported-but-legacy).
  New **§6.4 "Performance and the shared main thread"** makes the hot-path rules normative
  (SHOULD NOT do per-frame DOM/layout/IO; don't observe/mutate the shell — use contribution
  registries; suspend work when hidden; keep state per-instance). Replaces the previous "client
  runtime API is out of scope" placeholder. Settings/Styles/Static-assets renumbered to §6.5–6.7.
- Best-practices guide: added a **"Client screen & the shared main thread"** section grounded in
  real feedBack performance regressions — no DOM/layout work on a per-frame path, don't
  DOM-observe or mutate the app shell (use registration APIs instead of injecting into song/library
  cards), no synchronous storage/network on hot or gameplay-event paths, idempotent re-hydration
  (`plugin-runtime-idempotent.v1`), stop work when hidden, stay per-instance, and talk to other
  plugins through the capability `claim`/`dispatch`/`release` flow rather than their globals.
  Regrouped the guide (Getting started / Server routes / Client screen / Shipping) and expanded the
  pre-publish checklist with a client-performance block. Docs only.

## [0.1.0] - 2026-07-05

Initial draft of the feedBack plugin specification.

### Added
- Normative specification [`spec/plugin-spec-v1.md`](spec/plugin-spec-v1.md): conformance
  (RFC 2119 / RFC 8174), plugin anatomy, the `plugin.json` manifest reference, discovery and
  loading (the directory-name == `id` rule, bundled vs user-installed precedence, partial load,
  enable/disable), the client surface (screen, settings, styles, static assets), the server
  surface (`routes.py` `setup(app, context)`), capabilities and standards, versioning, and
  security considerations.
- [`spec/best-practices.md`](spec/best-practices.md): a non-normative best-practices guide with a
  pre-publish checklist.
- Manifest JSON Schema [`schemas/plugin.schema.json`](schemas/plugin.schema.json) (Draft 2020-12).
- Worked examples: [`examples/minimal-plugin`](examples/minimal-plugin) (manifest only) and
  [`examples/full-plugin`](examples/full-plugin) (screen, styles, settings, routes, capabilities).
- Reference validator [`tools/validate.py`](tools/validate.py): schema-checks a plugin manifest,
  enforces the directory-name rule, and confirms referenced files exist; doubles as the CI gate.
- Documentation site (MkDocs Material) assembled by `tools/gen_docs.py` and published to GitHub
  Pages, plus release-on-merge automation and a version-consistency guard
  (`tools/check_versions.py`).
- Repository governance: README, CONTRIBUTING (DCO + enhancement-proposal process), GOVERNANCE,
  CODE_OF_CONDUCT, issue templates, and AGPL-3.0-only licensing.

[Unreleased]: https://github.com/got-feedback/feedBack-plugin-spec/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/got-feedback/feedBack-plugin-spec/releases/tag/v0.1.0
