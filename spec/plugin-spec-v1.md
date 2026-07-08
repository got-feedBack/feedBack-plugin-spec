# feedBack Plugin Specification

- **Specification version:** 1.0.0
- **Manifest major version:** 1
- **Status:** Stable
- **Manifest file:** `plugin.json`

This document defines what a **feedBack plugin** is: the on-disk layout, the `plugin.json`
manifest, how the server discovers and loads a plugin, and the client and server surfaces a
plugin may contribute. It is the authoritative reference; where an implementation and this
document disagree, that is a bug in one of them, to be reconciled through the process in
[CONTRIBUTING.md](../CONTRIBUTING.md).

A companion [best-practices guide](best-practices.md) gives non-normative guidance on building
good plugins. This document is the *contract*; that one is the *advice*.

---

## 1. Conformance

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**,
**SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as described in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)
when, and only when, they appear in all capitals.

Two roles are referenced:

- A **Host** is the feedBack server (and its surrounding desktop app) that discovers, loads, and
  runs plugins.
- A **Plugin** is a directory conforming to this specification that the Host loads.

> **Naming note.** The project was renamed *slopsmith → feedBack*; the internal code and some
> environment variables still use the older name. Where this spec names an environment variable
> it gives the current name first and the legacy alias second. Both are honoured by the Host
> until the internal rename completes.

---

## 2. Overview

A plugin is a self-contained directory that extends feedBack with a new screen, a settings
panel, server endpoints, or a declared capability — in any combination. The design rests on
three ideas:

1. **The manifest is the contract.** A plugin is discovered and described entirely by its
   `plugin.json`. Nothing about a plugin is inferred by scanning for files the manifest does not
   declare.
2. **A plugin is a folder, identified by its `id`.** The directory name *is* the identity: it
   MUST equal the manifest `id`. This makes a plugin trivially installable (drop the folder in)
   and removable (delete it).
3. **Optional surfaces, loaded independently.** A plugin MAY contribute a client screen, a
   settings panel, server routes, a guided tour, and/or capability declarations. The Host loads
   each surface only if the manifest declares it; a plugin that fails to load one surface does
   not prevent the others (see [§5.4](#54-partial-load-and-failure)).

The smallest valid plugin is a directory containing a `plugin.json` with an `id` and nothing
else — it loads, contributes nothing, and does no harm.

---

## 3. Anatomy of a plugin

A plugin is a directory whose name equals its `id`:

```text
tuner/                     # directory name == manifest "id"
├── plugin.json            # REQUIRED — the manifest
├── screen.js              # client script entry (manifest "script")
├── src/                   # OPTIONAL — an ES-module tree the entry imports (see §6.8)
│   └── main.js
├── settings.html          # settings panel markup (manifest "settings.html")
├── routes.py              # server routes (manifest "routes")
├── assets/
│   └── plugin.css         # styles (manifest "styles")
└── tour.json              # optional guided tour (manifest "tour")
```

Only `plugin.json` is REQUIRED. Every other file exists **because the manifest points at it**;
a file present but not referenced from the manifest is ignored by the Host (though it MAY still
be served as a static asset — see [§6.7](#67-static-assets)).

The `script` entry MAY be a single self-contained file, or — when the manifest sets
`"scriptType": "module"` (see [§4.3](#43-client-surface-keys--script-screen-styles)) — a small ES
module that imports the plugin's client code from a **`src/` module tree**. The Host serves that
tree so the entry's relative imports resolve; see [§6.8](#68-splitting-client-code-across-modules).

File and directory names inside a plugin SHOULD be lowercase with `-` or `_` separators. The
directory name (the `id`) MUST match `^[a-z0-9][a-z0-9_-]*$` (see [§4.2](#42-id)).

---

## 4. The manifest — `plugin.json`

`plugin.json` MUST be a single JSON object encoded as UTF-8. Unknown keys MUST be ignored by the
Host, which is what makes the manifest forward-extensible: a new optional key is invisible to an
older Host.

The machine-readable schema is [`schemas/plugin.schema.json`](../schemas/plugin.schema.json)
(JSON Schema, Draft 2020-12). This section is the prose reference.

### 4.1. Field summary

| Key | Type | Req. | Meaning |
|---|---|---|---|
| `id` | string | **Yes** | Stable identity; MUST equal the directory name. |
| `name` | string | No | Human-readable display name. Defaults to `id`. |
| `version` | string | No | Plugin version (semver RECOMMENDED). |
| `description` | string | No | One-line description for listings. |
| `type` | string | No | Plugin kind, e.g. `"visualization"`. |
| `script` | string | No | Client JS entry, relative path (e.g. `screen.js`). |
| `scriptType` | string | No | How the Host loads `script`: `"module"` loads it as an ES module; absent or `"classic"` loads it as a classic script (see [§4.3](#43-client-surface-keys--script-screen-styles)). |
| `minHost` | string | No | Minimum Host (core) version the plugin requires (semver). Advisory in the current Host. |
| `screen` | string | No | Client screen markup, relative path (e.g. `screen.html`). |
| `styles` | string | No | CSS file, relative path (e.g. `assets/plugin.css`). |
| `settings` | object | No | Settings-panel declaration (see [§4.4](#44-settings)). |
| `routes` | string | No | Python module contributing server routes (see [§7](#7-server-surface)). |
| `tour` | string | No | Guided-tour definition, relative path (e.g. `tour.json`). |
| `icon` | string | No | Nav icon (emoji or asset reference). |
| `category` | string | No | Grouping hint for the plugin list. |
| `nav` | object/bool | No | Navigation-entry overrides. |
| `fullscreen` | bool | No | Screen requests a full-viewport layout. |
| `bundled` | bool | No | Declares the plugin as a first-party bundled plugin (see [§5.3](#53-bundled-vs-user-installed)). |
| `private` | bool | No | Marks the plugin as not for public listing. |
| `capabilities` | object | No | Capability declarations (see [§8](#8-capabilities-and-standards)). |
| `standards` | array of string | No | Standards the plugin claims to implement (see [§8](#8-capabilities-and-standards)). |
| `settings_schema` | object | No | Structured description of the plugin's stored settings. |
| `diagnostics` | object | No | Files to include in a diagnostics bundle. |

A Host MUST tolerate any additional keys. A Host MUST NOT fail to load a plugin because of an
unrecognised key.

### 4.2. `id`

`id` is REQUIRED and MUST be a non-empty string. It is the plugin's stable identity: it keys the
navigation entry, the settings store, the routes namespace, and the capability graph.

- The plugin's **directory name MUST equal `id`.** A Host that finds a directory whose name does
  not match the manifest `id` MUST NOT treat it as bundled and SHOULD skip or warn (see
  [§5.3](#53-bundled-vs-user-installed)).
- `id` MUST match `^[a-z0-9][a-z0-9_-]*$` (consistent with [§3](#3-anatomy-of-a-plugin), the
  manifest schema, and the reference validator, which all treat a non-conforming `id` as an
  error). A Host MUST reject a non-string or empty `id` — such a directory is not a plugin.
- `id` MUST be treated as a stable, public identifier. Changing a plugin's `id` is a new plugin,
  not a new version of the old one — it orphans stored settings keyed to the old `id`.

### 4.3. Client-surface keys — `script`, `screen`, `styles`

These declare the plugin's client (renderer) contribution. Each value is a path relative to the
plugin directory. See [§6](#6-client-surface) for how they are served.

- `script` — a JavaScript module that renders and drives the plugin's screen.
- `screen` — static markup for the screen (used with or instead of `script`).
- `styles` — a CSS file applied when the plugin's screen is active.

A plugin with none of these contributes no client screen (it may still contribute `routes`,
`settings`, or `capabilities`).

**Classic vs. module `script` (`scriptType`).** By default the Host loads `script` as a *classic*
browser script that runs in the global scope. When the manifest sets `"scriptType": "module"`, the
Host loads `script` as an ES module (`<script type="module">`) instead. A module entry MAY use
top-level `import` / `export` and `import.meta`, and MAY split the plugin's client code across a
tree of sibling modules it imports — conventionally under `src/`, with a one-line
`screen.js` of `import './src/main.js';`. The Host serves that tree so those imports resolve; see
[§6.8](#68-splitting-client-code-across-modules). A classic entry cannot use top-level `import` /
`export` and shares state across split files through `window` instead.

`scriptType` is additive: an older Host that does not recognise it loads `script` as a classic
script (where a module entry's top-level `import` fails). A plugin that requires module loading
therefore SHOULD declare the minimum Host version it needs via `minHost`, so a Host too old to load
it as a module can surface that rather than silently loading a broken screen.

### 4.4. `settings`

`settings` is an object declaring the plugin's settings panel and its persisted files:

```json
"settings": {
  "html": "settings.html",
  "category": "graphics",
  "server_files": ["plugin_uploads/highway_3d/current.mp4"]
}
```

- `settings.html` — REQUIRED within `settings`; path to the settings-panel markup.
- `settings.category` — OPTIONAL grouping hint (e.g. `graphics`, `audio`).
- `settings.server_files` — OPTIONAL list of Host-relative paths this plugin persists and that a
  settings export/import SHOULD carry with the plugin.

### 4.5. `version`

`version` is OPTIONAL but RECOMMENDED, and SHOULD be a semver string (`"1.3.3"`). It versions the
*plugin*, independent of this specification's version and of the manifest major version. The Host
surfaces it in the plugin list and the plugin manager uses it to decide whether an update is
available.

---

## 5. Discovery and loading

### 5.1. Where plugins are found

The Host discovers plugins by scanning one or more **plugin directories**, in order:

1. The in-tree bundled plugins directory shipped with the server.
2. Any directory named by the **`FEEDBACK_PLUGINS_DIR`** environment variable (legacy alias:
   **`SLOPSMITH_PLUGINS_DIR`**), when set and distinct from the bundled directory.
3. The Host's user-plugins directory (where the in-app Plugin Manager installs), under the
   platform config path.

Within each directory, the Host considers every immediate subdirectory that contains a
`plugin.json`. A subdirectory without a `plugin.json`, or whose `plugin.json` has no string `id`,
is silently skipped.

### 5.2. The directory-name rule

A candidate directory is loaded as the plugin `id` **only when the directory name equals the
manifest `id`.** This is the single most common discovery failure: a folder named `Tuner` or
`tuner-plugin` containing `{"id": "tuner"}` will not be discovered as `tuner`. Folder name and
`id` MUST match exactly, including case.

### 5.3. Bundled vs user-installed

When the same `id` is found more than once (e.g. a bundled copy and a user-installed copy), the
Host MUST pick exactly one:

- A copy is **bundled** only when *all three* hold: it lives in the in-tree bundled directory,
  its manifest sets `"bundled": true`, and its directory name equals its `id`.
- A **bundled** copy always wins over a non-bundled copy of the same `id`.
- When neither copy is bundled, a user-installed copy overrides an in-tree copy of the same `id`
  (this is how a user replaces a plugin without editing the tree).

A Host SHOULD keep an evicted copy as a fallback: if the winning copy fails to load its routes,
the Host MAY restore the evicted copy so the plugin keeps working.

### 5.4. Partial load and failure

Loading a plugin is not all-or-nothing. The Host loads each declared surface independently:

- A plugin whose `routes` module raises during import or `setup()` MUST NOT prevent its client
  screen or settings from loading, and MUST NOT abort discovery of other plugins.
- A plugin that is still installing dependencies or that failed to load SHOULD remain visible in
  the plugin list as a disabled entry carrying its status, rather than vanishing.

Because a Host web framework may offer no route-deregistration API, a `routes` module that
registers some handlers and *then* raises leaves those handlers mounted. A plugin's `setup()`
therefore SHOULD register routes only after its own validation has passed (see
[§7.3](#73-writing-a-robust-setup)).

### 5.5. Enable / disable

A Host MAY let a user disable a plugin. A disabled plugin is skipped at load (no screen, no
routes, no capabilities) but SHOULD remain listed as an "off" entry that can be switched back on.
The choice MUST persist across restarts. A Host MAY define a small set of plugins that cannot be
disabled because doing so would break core surfaces.

---

## 6. Client surface

A plugin with a `script` and/or `screen` contributes a navigable screen that runs in the app's
renderer. This section pins the **portable, stable** rules a screen must follow
([§6.4](#64-performance-and-the-shared-main-thread) especially), and describes the current
**Host-provided runtime surface** ([§6.3](#63-the-client-runtime-surface)) — which is versioned by
the Host and is **not** frozen by this specification version.

### 6.1. Screen mount lifecycle

The mount **mechanism** is defined and versioned by the Host, not by this document; the mechanics
below describe the current Host and are given so plugin authors can reason about lifecycle and
idempotence. What is **normative and stable** is the idempotence requirement at the end of this
section.

For each ready plugin that declares a `screen`, the Host:

1. creates a container element it owns — currently a `<div class="screen">` with a deterministic,
   `id`-derived identifier (of the form `plugin-<id>`) — and inserts it into the app shell;
2. sets that container's markup from the plugin's `screen` file;
3. loads the plugin's `script` — as a classic script, or as an ES module when the manifest sets
   `scriptType: "module"` ([§4.3](#43-client-surface-keys--script-screen-styles)) — and executes it
   once.

There is **no Host-invoked entry point** in either case: the Host does not call a `mount()`,
`init()`, or `render()` export. A plugin's `script` is a self-executing unit that runs on load
(a module entry runs once its static-import graph has evaluated), wires up its
own behaviour, and finds its own DOM by the identifiers the plugin authored inside its `screen`
markup. A plugin therefore SHOULD namespace those identifiers under its `id` so they don't collide
with the Host's or another plugin's — every plugin shares one document.

**Re-hydration (normative).** The Host MAY execute a plugin's `script` more than once in a session
— for example when the plugin set reloads. A plugin's `script` **MUST** be idempotent: a second
(or later) execution MUST NOT install a second copy of any listener, timer, observer, DOM subtree,
capability participant, or wrapped Host function. The established pattern is a guard on a
well-known global: a second run refreshes its implementation but installs shared listeners, timers,
and wrappers only once. This suppresses duplicate **global** side effects from re-execution; it is
distinct from **per-screen-instance** state, which [§6.4](#64-performance-and-the-shared-main-thread)
says to keep per instance (the Host may mount several instances of a screen at once). A plugin that
declares the `plugin-runtime-idempotent.v1` standard (see [§8](#8-capabilities-and-standards))
asserts exactly this property and MUST honour it.

### 6.2. Screen activation and visibility

A plugin's screen is not always visible. The Host activates exactly one screen at a time and
signals the transition; the current Host expresses activation by toggling an `active` class on the
screen container and emitting a `screen:changed` event (carrying the activated screen's id) on its
client event bus ([§6.3](#63-the-client-runtime-surface)).

A plugin SHOULD react to activation/deactivation rather than assuming it is always on screen, and
SHOULD suspend background work (animation loops, high-frequency subscriptions) while its screen is
not active — see [§6.4](#64-performance-and-the-shared-main-thread).

### 6.3. The client runtime surface

Beyond mounting a screen, the Host exposes a runtime surface a plugin MAY use. **This surface is
provided and versioned by the Host, and is not frozen by this specification version.** It is
described here so authors know what exists and how stable each part is; a future version of this
spec MAY pin parts of it normatively. There is no single global "Host version" — individual runtime
objects each carry their own `version` sentinel, and a plugin SHOULD feature-detect (check that an
object and its `version` exist) rather than assume.

The current surface has three tiers:

- **A client event bus** — a Host object (an `EventTarget`) offering `on` / `off` / `emit`, plus
  live state and transport helpers. The Host emits lifecycle events over it (screen activation,
  song load/ready, playback transport, position, library change). A plugin subscribes to react to
  app state. **Stable but general** — treat unknown events as optional.
- **Contribution registries** — Host APIs through which a plugin *registers* a contribution to a
  shared surface instead of mutating the shell's DOM (for example, registering a library-card
  action, or a renderer factory for a visualization). Using these is strongly preferred over
  reaching into shell DOM (see [§6.4](#64-performance-and-the-shared-main-thread)).
- **The capability control plane** — the versioned `claim` / `dispatch` / `release` /
  `registerParticipant` surface described in [§8](#8-capabilities-and-standards). This is the
  **forward-stable, explicitly-versioned** surface (`capability-pipelines.v1`) and is the preferred
  way for a plugin to drive or observe another plugin or a shared subsystem.

The current Host also exposes a set of **legacy global functions** (navigation, playback, and
library actions). These are **supported but legacy** — the Host is migrating them behind the
capability control plane. A plugin SHOULD prefer the capability surface and the contribution
registries over calling legacy globals, and MUST NOT assume any legacy global exists without
feature-detecting it.

### 6.4. Performance and the shared main thread

A plugin's `script` runs, unsandboxed, on the app's **shared main thread** — the same thread as a
real-time render loop that draws the note highway at up to ~60 frames per second and mutates the
DOM many times per second during playback. Main-thread time a plugin spends is time the render loop
does not have. Accordingly:

- A plugin **SHOULD NOT** perform DOM queries (`querySelector` / `querySelectorAll`), layout reads
  (`getBoundingClientRect`, `offsetWidth`/`offsetHeight`), or style writes on a **per-frame or
  high-frequency path** — inside a `requestAnimationFrame` loop, a render/`draw` callback, a short
  `setInterval`, or a `MutationObserver` callback. A plugin SHOULD resolve the elements it needs
  once, when its screen mounts, cache those references, and re-resolve only when a cached node has
  actually detached.
- A plugin **SHOULD NOT** observe or mutate the app shell's DOM (for example the song/library cards
  or the navigation bar) directly, and MUST NOT install a subtree `MutationObserver` on a shared
  container. To contribute UI to a shared surface, a plugin SHOULD use the Host's contribution
  registries ([§6.3](#63-the-client-runtime-surface)).
- A plugin **SHOULD NOT** perform synchronous storage (e.g. `localStorage`), blocking I/O, or
  network I/O on a per-frame path or in a handler for a high-frequency or gameplay event.
- A plugin **SHOULD** suspend animation loops and high-frequency subscriptions while its screen is
  not active ([§6.2](#62-screen-activation-and-visibility)), and **SHOULD** keep screen state
  per-instance rather than in module-level globals, because the Host MAY mount more than one
  instance of a screen at once (e.g. splitscreen), even though only one screen is *active* at a time
  ([§6.2](#62-screen-activation-and-visibility)).

These rules are portable and stable regardless of how the Host's runtime API evolves. The
non-normative [best-practices guide](best-practices.md) expands on them with examples.

### 6.5. Settings panel

When `settings.html` is declared, the Host renders it as the plugin's settings panel, grouped by
`settings.category`. Settings values a plugin persists are stored by the Host, keyed under the
plugin `id`.

### 6.6. Styles

When `styles` is declared, the Host applies that CSS while the plugin's screen is active. Plugin
CSS SHOULD be scoped to the plugin's own DOM to avoid leaking styles into the rest of the app.

### 6.7. Static assets

The Host MAY serve files inside a plugin directory as static assets (images, audio, fonts). A
plugin MUST NOT rely on any file *outside* its own directory being served, and MUST NOT assume a
particular absolute URL — asset URLs are Host-assigned relative to the plugin.

### 6.8. Splitting client code across modules

A plugin whose `script` declares `"scriptType": "module"` ([§4.3](#43-client-surface-keys--script-screen-styles))
MAY split its client code across several ES modules instead of shipping one file. The established
layout is a one-line entry (`screen.js` → `import './src/main.js';`) over a **`src/` tree** of
modules that `import` / `export` from one another.

For those imports to resolve in the browser, the Host serves the `src/` tree in addition to
`assets/` ([§6.7](#67-static-assets)): the entry's relative `import './src/…'` and any imports
between `src/` modules are fetched from the plugin, path-traversal-guarded the same way assets are.
A module resolves its own non-JS assets (worklets, wasm, CSS) against its module URL — e.g.
`new URL('../assets/worklet.js', import.meta.url)` — rather than a hardcoded absolute path.

This is a Host capability, not a bundler: the Host serves the module files verbatim and the browser
resolves the graph. The **exact URL layout** by which `src/` is served is Host-provided and versioned
by the Host (like the rest of [§6.3](#63-the-client-runtime-surface)); what this specification pins is
that a module entry's own-directory relative imports are served, and that the re-hydration idempotence
requirement of [§6.1](#61-screen-mount-lifecycle) applies to a module entry exactly as to a classic one.

A plugin that does not set `scriptType: "module"` keeps the classic single-`script` contract; serving
of a `src/` tree is meaningful only for a module entry.

---

## 7. Server surface

### 7.1. The `routes` module

When `routes` names a Python file, the Host imports it as a module and, if it defines a `setup`
function, calls it:

```python
# routes.py
from fastapi import FastAPI

def setup(app: FastAPI, context: dict) -> None:
    ...
```

- `setup` is OPTIONAL; a `routes` module without it is imported for its side effects only (not
  recommended).
- `setup` MUST be idempotent-safe to import: importing the module MUST NOT perform I/O or block.
  Do work inside `setup`, not at module top level.

### 7.2. The `context` argument

`context` is a dict the Host passes to `setup`. It carries at least:

- `config_dir` — a filesystem path where the plugin MAY read and write its own persisted state
  (e.g. `config_dir / "tuner.json"`).
- `log` — a logger the plugin SHOULD use, so its output lands in the Host's log stream under the
  plugin namespace.

A Host MAY add further keys; a plugin MUST tolerate keys it does not recognise and MUST NOT assume
a key beyond those listed above without a documented Host version that guarantees it.

### 7.3. Writing a robust `setup`

Because partially-registered routes cannot always be removed (see [§5.4](#54-partial-load-and-failure)),
a `setup` SHOULD:

- validate its configuration and inputs *before* registering any route;
- namespace its routes under a path derived from the plugin `id` (e.g. `/api/plugin/<id>/...`) to
  avoid colliding with the Host or other plugins;
- never raise after the first route is registered, if it can be avoided.

### 7.4. Route namespacing

A plugin MUST NOT register routes that collide with Host routes or with another plugin's routes.
Deriving every route path from the plugin `id` is the RECOMMENDED way to guarantee this.

---

## 8. Capabilities and standards

A plugin MAY declare **capabilities** and the **standards** it implements, so the Host can wire
it into cross-plugin pipelines (for example, the diagnostics and capability-inspection surfaces).

- `standards` is an array of standard identifiers the plugin claims to implement (e.g.
  `"capability-pipelines.v1"`, `"plugin-runtime-idempotent.v1"`).
- `capabilities` is an object keyed by capability domain; each declaration describes how the
  plugin participates in that domain:

```json
"capabilities": {
  "audio-input": {
    "roles": ["provider", "observer"],
    "operations": ["source.enumerate", "source.open", "source.close"],
    "events": ["source-registered", "source-selected", "source-opened", "permission-denied"],
    "mode": "active",
    "compatibility": "none",
    "ownership": "multi-provider",
    "safety": "sensitive",
    "version": 1,
    "description": "Provides native desktop audio input devices to the audio-input control plane."
  }
}
```

The **domain keys** (`audio-input`, `diagnostics`, `playback`, …) and the field **vocabulary**
below are **open and defined by the standard the plugin declares** (e.g. `capability-pipelines.v1`),
not closed by this document. A Host MUST ignore declaration fields it does not recognise, exactly
as it does for unknown manifest keys ([§4](#4-the-manifest--pluginjson)). The commonly-used fields
are:

- `roles` — the roles the plugin plays in the domain (e.g. `provider`, `observer`, `owner`,
  `requester`).
- **Verb/action tokens** the plugin services — one or more of `operations`, `commands`, or
  `requests` (arrays of string tokens; a domain/standard picks which name it uses).
- **Event tokens** — arrays of string tokens naming events. `events` and `emits` are events the
  plugin **emits**; `observes` is events the plugin **observes** (a domain/standard picks which
  names it uses).
- `mode` — participation mode (e.g. `active`).
- `kind` — a domain-specific classifier for the declaration (e.g. `command`).
- `compatibility` — how the plugin behaves against an incompatible counterpart; observed values
  are `none`, `shim-allowed`, `degrade-noop`, `required`, `legacy-window-shim` (open set).
- `ownership` — the plugin's ownership stance in the domain (e.g. `multi-provider`,
  `exclusive-owner`, `diagnostic-only`).
- `safety` — a safety classification for the declaration (e.g. `safe`, `sensitive`,
  `diagnostic-only`).
- `version` — the declaration's integer version.
- `description` — a human-readable description of the declaration.

A disabled plugin contributes nothing to any capability pipeline: the Host MUST treat a disabled
plugin as declaring no capabilities, regardless of what its manifest says.

Capabilities are an advanced, evolving surface whose precise semantics live in the capability
standards, not here. A plugin that does not participate in a pipeline simply omits `capabilities`
and `standards`.

---

## 9. Versioning and compatibility

Three version axes are kept separate:

1. **This specification's version** — the document you are reading (`0.1.0`), frozen per release.
2. **The manifest major version** — the shape of `plugin.json` (currently `1`). A backward-
   incompatible change to the manifest shape is a new manifest major version.
3. **A plugin's own `version`** — independent of both of the above.

The manifest is designed to grow **additively**. New capability arrives as a new OPTIONAL key
that an older Host ignores. Removing, renaming, or repurposing an existing key is a breaking
change and requires a manifest-major bump — see [CONTRIBUTING.md](../CONTRIBUTING.md) for the
process and [GOVERNANCE.md](../GOVERNANCE.md) for how such changes are decided.

Compatibility rules of thumb:

- A Host MUST ignore manifest keys it does not recognise.
- A plugin SHOULD degrade gracefully on an older Host: a surface the Host does not support is
  simply not loaded, and the plugin's other surfaces MUST still work.

---

## 10. Security considerations

A plugin runs with the Host's privileges: its `routes` module executes arbitrary Python in the
server process, and its `script` runs in the app's renderer. Installing a plugin is therefore a
trust decision equivalent to installing an application extension.

- A Host SHOULD make the trust boundary explicit when a user installs a non-bundled plugin.
- A plugin MUST confine filesystem writes to its `config_dir` and its declared `server_files`; it
  MUST NOT write elsewhere in the Host's config or data directories.
- A plugin MUST NOT read another plugin's stored settings.
- A plugin SHOULD validate all input to its routes; it is exposed on the same origin as the Host.

---

## 11. Glossary

- **Host** — the feedBack server + desktop app that loads and runs plugins.
- **Manifest** — the `plugin.json` file describing a plugin.
- **Surface** — an independently-loaded contribution: screen, settings, routes, tour, or
  capabilities.
- **Bundled plugin** — a first-party plugin shipped in-tree, marked `"bundled": true`, whose
  folder name equals its `id`.
- **Capability** — a declared participation in a cross-plugin pipeline.
