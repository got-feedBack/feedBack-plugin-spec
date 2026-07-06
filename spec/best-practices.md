# feedBack plugin best practices

Practical, non-normative guidance for building good feedBack plugins. The
[specification](plugin-spec-v1.md) is the contract — what a plugin *must* do to load. This guide
is the advice — what a plugin *should* do to be a good citizen. Nothing here overrides the spec.

If you are writing your first plugin, start from [`examples/minimal-plugin`](../examples/minimal-plugin)
and grow it toward [`examples/full-plugin`](../examples/full-plugin).

---

## Getting started

### 1. Start from the smallest thing that loads

The smallest valid plugin is a folder with one file:

```text
my-plugin/
└── plugin.json      →  {"id": "my-plugin", "name": "My Plugin"}
```

Get *that* discovered first (folder name equal to `id`, dropped into a plugins directory), then
add one surface at a time — a screen, then settings, then routes. Adding surfaces incrementally
means when something stops loading you know exactly which change caused it.

### 2. Treat the `id` as forever

The `id` keys your settings store, your routes namespace, and your capability declarations.
Renaming it silently orphans every user's saved settings. Pick a lowercase, `-`/`_`-separated,
descriptive `id` once (`drum_highway_3d`, not `dh3` or `DrumHighway`) and never change it. The
folder name must match it exactly.

### 3. Keep the manifest declarative

Every file your plugin uses at load time should be *pointed at* from the manifest — `script`,
`screen`, `styles`, `settings.html`, `routes`, `tour`. If the Host has to guess a filename, a
future Host change can break you. Conversely, don't reference files you don't ship.

### 4. Version your plugin with semver

Set `version` and bump it on every release: PATCH for fixes, MINOR for new optional behaviour,
MAJOR when you change or remove behaviour users depend on. The plugin manager uses it to detect
updates, and users use it to report bugs against a known build.

---

## Server routes

### 5. Do nothing at import time

```python
# Good — all work happens inside setup()
from fastapi import FastAPI

def setup(app: FastAPI, context: dict) -> None:
    config_dir = Path(context["config_dir"])
    log = context.get("log") or logging.getLogger("feedBack.plugin.my_plugin")
    ...
```

Importing your `routes` module must be cheap and side-effect-free: no network calls, no file
reads, no blocking. The Host imports every plugin's routes during startup; slow or failing
imports slow or break the whole load.

### 6. Register routes only after you've validated

The Host may be unable to *un*-register a route once mounted. So validate configuration, open
files, and check inputs **before** the first `app.get(...)` / `app.post(...)`. A `setup()` that
mounts two routes and then throws leaves two half-working endpoints behind permanently.

### 7. Namespace everything under your `id`

- Routes: `"/api/plugin/my-plugin/state"`, not `"/state"`.
- CSS: scope selectors to your screen's root element, don't style bare `body`/`h1`.
- Persisted files: write under the `config_dir` the Host hands you, in a file named for your
  plugin (`config_dir / "my_plugin.json"`).

Collisions with the Host or another plugin are silent and maddening; namespacing prevents them.

### 8. Persist state where the Host tells you

Read and write only inside `context["config_dir"]` and any paths you declared in
`settings.server_files`. Never write elsewhere in the Host's config/data tree, and never read
another plugin's files. This is what keeps export/import, backups, and uninstall clean.

---

## Client screen & the shared main thread

Your `script` does **not** run in a sandbox. It executes in the app's own document and global
scope, on the **same main thread** as everything else — including a real-time note-highway that
renders at ~60 fps and mutates the DOM many times per second during play. Every millisecond your
screen spends on the main thread is a millisecond the render loop doesn't have. Most plugin
performance regressions in feedBack's history came from this one fact. The rules below are the
ones that were learned the hard way.

### 9. Never touch the DOM or read layout on a per-frame / high-frequency path

Do **not** call `querySelector` / `querySelectorAll`, read layout (`getBoundingClientRect`,
`offsetWidth`, `offsetHeight`), or write styles inside anything that fires at frame rate:
`requestAnimationFrame` callbacks, a `draw()` loop, a short `setInterval`, or a `MutationObserver`
callback.

> A real profiled lag report in feedBack traced to **three plugins each doing a `querySelectorAll`
> every frame** — together ~18% of main-thread CPU, all of it stolen from the render loop.

Resolve the elements you need **once, on mount**, cache the references, and re-resolve only when a
cached node has actually detached (`!el.isConnected`). Reading layout and writing styles in the
same high-frequency pass also forces synchronous reflow ("layout thrash") — batch all reads, then
all writes.

### 10. Don't observe or mutate the app shell — use the registration APIs

It is tempting to reach into the app's own UI — the song/library cards, the nav bar, the transport
— with `document.querySelector` and inject or rewrite nodes. Don't. The shell re-renders those
regions (the library grid is virtualized and repaints on every scroll frame and on score updates),
so anything you inject gets clobbered, and a `MutationObserver` watching a shared container fires
on **every** one of those repaints.

> feedBack specifically removed a legacy pattern where several plugins added buttons to song cards
> by DOM-observing `.song-card`; it was replaced with a Host-provided **card-action registration
> API** for exactly this reason.

So:

- Contribute UI to a shared surface through the Host's registration API for that surface, not by
  mutating its DOM.
- Never `MutationObserver.observe(document.body, { subtree: true })` (or any shared container with
  `subtree: true`) — it turns every shell mutation into your work.
- Keep any predicate the Host calls per item (e.g. "does this card-action apply to this song?")
  **O(1) and allocation-free** — it runs once per visible card on every re-render.

### 11. No synchronous network or storage on a hot or fan-out path

`localStorage` is synchronous; `fetch`/`await` stalls your handler on I/O. Neither belongs in a
handler that fires per note, per frame, or on a high-frequency event. The worst offender is doing
this in response to a gameplay event (a song-complete / score event can arrive at the exact moment
the frame budget is tightest). Read settings once on mount and cache them; debounce writes to an
idle callback or a single `requestAnimationFrame`.

### 12. Make re-hydration idempotent (`plugin-runtime-idempotent.v1`)

The Host may **re-run your `script` mid-session** (for example when the plugin set reloads). If a
second run installs another event wrapper, timer, observer, DOM root, or capability participant,
you now have duplicates — a class of bug that has duplicated audio signal chains in practice.

Make a second run a **no-op**. The established pattern is a stable singleton on `window`:

```js
// Idempotent (plugin-runtime-idempotent.v1): re-hydration replaces impl, installs nothing twice.
const hooks = (window.__feedBackMyPluginHooks ||= { installed: false, impl: null });
hooks.impl = makeImpl();           // always refresh the implementation
if (hooks.installed) return;       // …but wire listeners/timers/wrappers only once
hooks.installed = true;
```

Only put `"plugin-runtime-idempotent.v1"` in your manifest `standards` once this is actually true
of your screen.

### 13. Stop work when your screen is hidden, and stay per-instance

- When your screen is not the active one, cancel your `requestAnimationFrame` loop and unsubscribe
  from playback/gameplay events. A background plugin animating or listening during play is pure
  waste on the hottest path.
- Keep all state **per screen instance**, not in module-level globals — feedBack can show two
  screens at once (splitscreen), so a global counter or a single cached element handle will fight
  itself across instances.

### 14. Talk to other plugins through capabilities, not their globals

To drive another plugin or a shared subsystem, use the capability pipeline's
`claim` / `dispatch` / `release` flow rather than reaching into another plugin's `window` globals
or internal objects. Declare your own participation honestly (`roles`, `ownership`, `safety`) and
service only the commands/events you actually implement. Reaching into foreign globals is exactly
the coupling the capability system exists to remove, and it breaks the moment that plugin reloads.

---

## Shipping & good citizenship

### 15. Fail soft, log clearly

- Use `context["log"]` (server) so your messages land in the Host log under your plugin's
  namespace.
- A missing config file should mean "use defaults", not a crash. Read tolerantly (see the
  [full example](../examples/full-plugin/routes.py)).
- If a surface can't initialise, degrade to a reduced-but-working state rather than taking the
  whole plugin down.

### 16. Degrade gracefully across Host versions

A plugin may run on a Host older than the one you developed against. Don't assume a `context` key
or a client runtime API exists without a documented Host version guaranteeing it. If an optional
surface isn't supported, your plugin's other surfaces must still work.

### 17. Only declare capabilities you actually implement

`capabilities` and `standards` wire you into cross-plugin pipelines (diagnostics, capability
inspection). Declaring a capability you don't service registers a phantom participant and breaks
the pipeline. If you don't participate, omit both keys entirely.

### 18. Mind the security boundary

Your `routes` run arbitrary Python in the server process and your `script` runs in the app's
renderer. Validate every route input, don't shell out on user data, and don't reach outside your
plugin directory. Users installing your plugin are trusting it like an app extension — earn it.

### 19. Ship a README and a changelog

A plugin folder should carry a short `README.md` (what it does, which Host version it targets) and
note changes per version. It costs little and saves every future reader — including you.

---

## Checklist before you publish

- [ ] Folder name equals `id`, matching `^[a-z0-9][a-z0-9_-]*$`.
- [ ] `plugin.json` is valid against [`schemas/plugin.schema.json`](../schemas/plugin.schema.json)
      (`python tools/validate.py path/to/my-plugin`).
- [ ] Every manifest file reference resolves to a shipped file.
- [ ] `routes.py` does no work at import time; `setup()` validates before registering.
- [ ] Routes, CSS, and persisted files are namespaced under the `id`.
- [ ] `version` is set and follows semver.

**Client-screen performance (if you ship a `script`):**

- [ ] No `querySelector`/layout reads/style writes inside `requestAnimationFrame`, `draw()`, short
      `setInterval`, or `MutationObserver` callbacks — element refs resolved once on mount.
- [ ] No `MutationObserver` on a shared shell container with `subtree: true`; shell UI contributed
      via registration APIs, not DOM injection.
- [ ] No synchronous `localStorage` or `await fetch` on a per-frame / per-note / gameplay-event path.
- [ ] Re-running `script` is a no-op (idempotent hydration) if you declare
      `plugin-runtime-idempotent.v1`.
- [ ] rAF loops and event subscriptions stop when the screen is hidden; state is per-instance.

**Capabilities & shipping:**

- [ ] Capabilities/standards declared only if actually implemented; cross-plugin calls go through
      `claim`/`dispatch`/`release`, not foreign globals.
- [ ] A `README.md` states purpose and target Host version.
