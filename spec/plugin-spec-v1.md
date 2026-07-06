# feedBack Plugin Specification

- **Specification version:** 0.1.0
- **Manifest major version:** 1
- **Status:** Draft
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
├── screen.js              # client script (manifest "script")
├── settings.html          # settings panel markup (manifest "settings.html")
├── routes.py              # server routes (manifest "routes")
├── assets/
│   └── plugin.css         # styles (manifest "styles")
└── tour.json              # optional guided tour (manifest "tour")
```

Only `plugin.json` is REQUIRED. Every other file exists **because the manifest points at it**;
a file present but not referenced from the manifest is ignored by the Host (though it MAY still
be served as a static asset — see [§6.4](#64-static-assets)).

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
| `script` | string | No | Client JS module, relative path (e.g. `screen.js`). |
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

### 6.1. Screen

A plugin with a `script` and/or `screen` contributes a navigable screen. The Host adds a
navigation entry (labelled by `name`, iconed by `icon`) that activates the screen.

`script` is loaded as a client-side JavaScript module. The runtime API available to that
module (how it mounts, reads settings, and talks to its own `routes`) is provided by the Host and
is **out of scope for this version of the spec** — it is documented by the Host's own developer
docs and is evolving. A future version of this spec SHOULD pin that API. Until then, a plugin
targeting a specific Host version SHOULD record which Host runtime it was written against.

### 6.2. Settings panel

When `settings.html` is declared, the Host renders it as the plugin's settings panel, grouped by
`settings.category`. Settings values a plugin persists are stored by the Host, keyed under the
plugin `id`.

### 6.3. Styles

When `styles` is declared, the Host applies that CSS while the plugin's screen is active. Plugin
CSS SHOULD be scoped to the plugin's own DOM to avoid leaking styles into the rest of the app.

### 6.4. Static assets

The Host MAY serve files inside a plugin directory as static assets (images, audio, fonts). A
plugin MUST NOT rely on any file *outside* its own directory being served, and MUST NOT assume a
particular absolute URL — asset URLs are Host-assigned relative to the plugin.

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
  "diagnostics": {
    "roles": ["requester", "observer"],
    "commands": ["snapshot"],
    "events": [],
    "mode": "active",
    "compatibility": "none",
    "ownership": "diagnostic-only",
    "safety": "diagnostic-only",
    "version": 1
  }
}
```

Recognised fields within a declaration:

- `roles` — the roles the plugin plays in the domain (e.g. `requester`, `observer`).
- `commands` — commands the plugin can service.
- `events` — events the plugin emits.
- `mode` — participation mode (e.g. `active`).
- `compatibility` — one of `none`, `shim-allowed`, `degrade-noop`, `required`,
  `legacy-window-shim`.
- `ownership`, `safety` — domain-specific classification (e.g. `diagnostic-only`).
- `version` — the declaration's integer version.

A disabled plugin contributes nothing to any capability pipeline: the Host MUST treat a disabled
plugin as declaring no capabilities, regardless of what its manifest says.

Capabilities are an advanced, evolving surface. A plugin that does not participate in a pipeline
simply omits `capabilities` and `standards`.

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
