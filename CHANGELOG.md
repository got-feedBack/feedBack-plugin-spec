# Changelog

All notable changes to the feedBack plugin specification are documented here.

This repository is licensed under [AGPL-3.0-only](LICENSE). This file follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the specification is versioned per
[Semantic Versioning](https://semver.org/) — see [spec §9](spec/plugin-spec-v1.md#9-versioning-and-compatibility)
for how the document, manifest, and per-plugin versions relate.

## [Unreleased]

### Added
- **Module `script` entries.** §3 (Anatomy), §4.1/§4.3, new §6.8 (Splitting client code), and
  `schemas/plugin.schema.json` document the optional **`scriptType`** manifest key: `"module"` loads
  a plugin's `script` as an ES module (`<script type="module">`), letting the entry use top-level
  `import` / `export` and `import.meta` and split its client code across a served **`src/`** module
  tree; absent or `"classic"` is the unchanged classic-script behaviour. The optional **`minHost`**
  key (minimum Host version) is documented alongside it. Purely additive — every existing manifest
  still validates, and a Host that ignores `scriptType` keeps loading `script` as a classic script.

### Changed
- Best-practices "Organizing client code across files" (rules 27–29) rewritten around the new
  paradigm: an ES-module entry (`scriptType: "module"` + a `src/` tree with real `import`/`export`)
  is now the recommended way to split client code, with the classic single-`screen.js` bundle /
  `window`-shared runtime split kept as the fallback for older Hosts. Corrects the prior text, which
  stated `screen.js` is *always* a classic script and that only `assets/` is servable — both no
  longer true once `scriptType: "module"` is set.

## [1.0.0] - 2026-07-06

First stable release of the feedBack plugin specification. Marks the normative spec and its
companion best-practices guide (54 rules, ground-truthed against the app) as stable, consolidating
everything accumulated since the 0.1.0 draft. The version string moves 0.1.0 → 1.0.0 and the
document status changes from Draft to Stable.

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
- Best-practices guide: added a **"Visualizations"** section for `type: "visualization"` plugins,
  ground-truthed against the Host's renderer contract and recent splitscreen/settings fixes. Covers
  the **factory pattern** (`window.feedBackViz_<id>` returns a fresh renderer per call — required for
  splitscreen's N simultaneous panels), the renderer interface (`draw`/`init`/`resize`/`destroy`/
  `contextType`), per-instance resource ownership and `destroy()` cleanup, treating the per-frame
  bundle as read-only, self-detecting canvas size drift, and **communicating settings via
  `applySetting(key, value)` per instance** (declare `settings` on the `visualization` capability;
  the Host applies each change to the specific per-panel instance) — including the concrete failure
  modes recent fixes addressed (apply-live-not-reload, no cross-setting leakage, deliberate
  per-panel vs global key scoping, fan-out to all panels, settings panel loads before the renderer),
  and persistence guidance (Host owns persistence — don't hand-roll `localStorage`; if self-managed,
  stage an in-memory fallback before the quota-fallible `setItem` and keep it off the per-frame path),
  plus the fail-safe auto-revert. Expanded the checklist with a Visualizations block. Docs only.

- Best-practices guide: expanded the `id`/naming rule (rule 2) with the collision and namespacing
  gotchas, ground-truthed against the loader. Explains how far the `id` reaches (routes module
  `plugin_<id>_routes`, screen container `plugin-<id>`, viz global `window.feedBackViz_<id>`,
  diagnostics path, `localStorage` prefix), the exact-case folder rule and why the charset matters
  (it becomes a Python module + DOM/JS identifiers), the **collision resolution** (a bundled `id`
  always wins — a user plugin reusing it is silently ignored; between two non-bundled plugins the
  first discovered wins), **reserved ids** (`capability_inspector`, `app_tour_*` are always-enabled),
  and namespacing shared-space names (`localStorage`, `window` globals, routes, CSS) by `id`. Added
  matching checklist items. Docs only.
- Best-practices guide: added a **"Minigames"** section for plugins that register into the bundled
  `minigames` host, ground-truthed against the host + SDK. Covers **late-binding registration** (the
  host loads after your plugin — queue via `window.__feedBackMinigamesPending` and/or the
  `feedBack-minigames-ready` event), the `minigame` manifest block with `spec.id` === plugin `id`,
  the `start`/`stop` lifecycle where **the game must release everything it opens** (rAF loops,
  `AudioContext`, `getUserMedia`, timers, listeners — the host only cancels its own), supersede-safe
  `start` (double-tap / navigate-away races), standalone-by-default vs `usesPlayer`, and host-owned
  scoring/persistence (report via the SDK; single active session). Added a Minigames checklist block.
  Docs only.
- Best-practices guide: added an **"Organizing client code across files"** section for splitting a
  plugin's client JS instead of shipping one monolithic `screen.js`, ground-truthed against how the
  Host loads and serves plugin JS. Covers bundling to one `screen.js` as the simplest path;
  the constraint that `screen.js` is a **classic script** (no `import`/`export`/`import.meta` — split
  files share state via `window`); serving extra files from **`assets/`** (the plugin root isn't
  servable) referenced by **absolute `/api/plugins/<id>/…` URLs** (relative resolves against the
  document, not the script); and **idempotent** runtime loading so re-hydration doesn't double-load.
  Added a matching checklist block. Docs only.
- Best-practices guide: added an **"Integrating with the app"** section, ground-truthed against the
  `window.feedBack` runtime surface. Adds the **event-bus catalog** (`screen:changed`, `song:*`,
  `library:changed`, `viz:*`, `highway:*` with their `event.detail` payloads), the rule to **drive
  the app through the `feedBack` API** (`navigate`/`getNavParams`/`playSong`/`seek`/`setLoop`/
  `currentSong`/`playQueue`) **rather than its DOM controls**, **wrapper discipline** for hooking
  Host globals (call and `await` the original, install once, clean up, no load-order assumptions),
  and the **v2/v3 player-chrome** mount contract. Added a matching checklist block. Docs only.
- Best-practices guide: added a **"Server-side robustness"** section for `routes`-shipping plugins,
  ground-truthed against the loader. Covers **declaring Python deps in `requirements.txt`** (no
  manifest field; installs are hash-keyed, sequential, and delay later plugins — keep them minimal
  and pinned; a failed install is non-fatal so guard heavy/optional imports), **not blocking the
  event loop** (a fast `setup()` killed at a ~60s timeout; a blocking `async def` handler freezes the
  server — use non-blocking I/O or a plain `def` that runs in the threadpool), **splitting server
  code via `context["load_sibling"]`** rather than bare imports that collide across plugins in
  `sys.modules`, and **logging through `context["log"]` (never `print()`)** plus route namespacing.
  Added a matching checklist block. Docs only.
- Best-practices guide: added a **"Styling"** section. A plugin can't rely on the app's compiled
  stylesheet (it only contains classes the bundled code uses), so a runtime-installed plugin renders
  unstyled unless it **ships its own compiled stylesheet via `styles`**. Covers building it to
  coexist — base/preflight reset **off**, selectors scoped, **no Tailwind Play CDN / runtime CSS
  engine** (slow, offline-hostile), and bump `version` to cache-bust the sheet. Added a matching
  checklist block. Docs only.
- Best-practices guide: added a **"Diagnostics"** section. Covers contributing plugin state to the
  user-exportable diagnostics bundle — **client** via `window.feedBack.diagnostics.contribute(id,
  payload)` (idempotent; last snapshot before export wins) and **server** via `diagnostics.server_files`
  / `diagnostics.callable` (`"module:function"` returning dict/list/bytes/str; the Host catches exceptions
  so a broken function never crashes the export) — and the rule that a bundle is effectively public,
  so it **MUST NOT contain secrets, credentials, absolute paths, usernames, or raw user content** and
  should stay small with a `schema` field. Added a matching checklist block. Docs only.

- Best-practices guide: added an **"Extending the app's shared surfaces"** section — the
  registration APIs rule 10 points authors to but never named. Covers **song/library card actions**
  (`window.feedBack.libraryCardActions.register(spec)` with `applies`/`enabled`/`run`), **nav entries**
  (the manifest `nav` key), **keyboard shortcuts** (`window.registerShortcut` with scoped lifetimes,
  cleaned up on teardown), and **audio faders** (`window.feedBack.audio.registerFader`, gated on
  `feedBack:audio:ready`, plugin owns persistence). Added a matching checklist block. Docs only.

- Best-practices guide: added **"Onboarding tours"** and **"Library providers"** sections, the
  last of the extension points a completeness sweep found. Tours: any plugin can ship a guided tour
  as a declarative `tour.json` (a `tour` manifest key; steps are centered `bubble`s or element
  `spotlight`s with `selector`/`waitFor`), with the client `window.feedBackTour.register(...)` API
  reserved for dynamic steps and offering the tour once. Library providers: add song sources via
  `context["register_library_provider"]` (unregister on teardown; the Host enforces owner attribution
  and the built-in `local` provider can't be removed; declare the `library` capability and page large
  sources). Added matching checklist items. Docs only.

- Best-practices guide: added a **"Highway overlays and note-state providers"** section for
  plugins that participate in the note-highway *without* replacing its renderer. Covers **overlays**
  (a layer on top of whatever renderer is active — own your rAF + canvas, re-read state each frame,
  respect lefty/invert, gate the built-in `project`/`fretX` geometry helpers on
  `highway.isDefaultRenderer()`, track the `highway:visibility` event for sibling DOM, clean up on
  toggle-off; not `type: "visualization"`, not in the picker), and the **note-state provider**
  (`highway.setNoteStateProvider(fn)` — a scorer lights the note gem itself on a correct hit; a single
  global surface, cleared on stop). Added matching checklist items. Docs only.

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

[Unreleased]: https://github.com/got-feedback/feedBack-plugin-spec/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/got-feedback/feedBack-plugin-spec/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/got-feedback/feedBack-plugin-spec/releases/tag/v0.1.0
