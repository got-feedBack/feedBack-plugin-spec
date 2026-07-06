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

### 2. Choose the `id` carefully — it's a permanent, far-reaching identifier

Your `id` is not just a label; the Host derives a surprising amount of machinery from it. It keys
the settings store, the routes namespace, and the capability participant, and it is interpolated
into names all over the app: the server routes module (`plugin_<id>_routes`), the screen container
element (`plugin-<id>`), a visualization's factory global (`window.feedBackViz_<id>`), the
diagnostics path (`plugins/<id>/`), and the conventional `localStorage` prefix. A collision or a
rename therefore ripples through all of them at once.

So:

- **Pick it once and never change it.** Renaming an `id` silently orphans every user's saved
  settings and breaks every derived name above. Changing the `id` is a *new* plugin, not a new
  version (see [spec §4.2](plugin-spec-v1.md#42-id)).
- **Make it specific and unique.** Prefer a descriptive `id` (`drum_highway_3d`, not `dh3` or a
  generic `player`/`viz`). A generic `id` is the easiest way to collide with someone else's plugin.
- **The folder name MUST equal the `id`, exactly, including case.** A folder named `Tuner` or
  `tuner-plugin` holding `{"id": "tuner"}` is simply not discovered — the most common "why won't my
  plugin load?" (see [spec §5.2](plugin-spec-v1.md#52-the-directory-name-rule)).
- **Stick to `^[a-z0-9][a-z0-9_-]*$` (lowercase, with `-` or `_` separators — both are fine and
  both are used in practice).** The charset isn't
  cosmetic: the `id` is spliced into a Python module name and DOM/JS identifiers. Uppercase breaks
  the exact-match discovery rule, and dots/spaces/other punctuation break module or element naming.
  The reference validator rejects anything outside this set — run it (`python tools/validate.py`).

**Collisions with an existing plugin.** When two plugins share an `id`, only one loads, and the
rule is not "last one wins":

- A **bundled** (first-party) plugin **always wins** — a plugin you install that reuses a bundled
  `id` is silently ignored (the Host keeps it only as a fallback if the bundled copy fails). Before
  naming a plugin, make sure the `id` isn't already a bundled one.
- Between two non-bundled plugins, the first the Host discovers wins and the other is dropped — so a
  duplicate `id` means one of them silently doesn't load.

**Reserved ids.** Do not name a plugin `capability_inspector`, or use an `app_tour_` prefix, unless
you intend to replace those core surfaces — the Host treats them as always-enabled (they cannot be
disabled), so a collision there is especially sticky.

**Namespace what the `id` doesn't namespace for you.** Because every plugin shares one `window` and
one document, prefix anything you put in a shared space with your `id`: `localStorage` keys, any
`window` globals you must expose, your routes (`/api/plugin/<id>/…`, rule 7), and your CSS (rule 10).
Two plugins writing `window.state` or `localStorage["theme"]` clobber each other silently.

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

### 11. No synchronous storage or awaited I/O on a hot or fan-out path

`localStorage` is synchronous — it blocks the main thread while it runs. `fetch` is asynchronous,
but *awaiting* a network round-trip inside a hot handler still stalls that handler on I/O. Neither
a synchronous `localStorage` call nor an awaited `fetch` belongs in a handler that fires per note,
per frame, or on a high-frequency event. The worst offender is doing
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

## Visualizations

A plugin whose manifest sets `"type": "visualization"` can replace the app's note-highway
renderer. The Host runs this renderer inside its own ~60 fps draw loop, and — critically — the app
can show **several highways at once** (splitscreen). Everything below exists so one renderer works
correctly when the Host makes many copies of it. The mechanism names here (the `feedBackViz_<id>`
factory global, the renderer methods, `applySetting`) are the **current Host contract**; treat the
principles as stable and the exact API as Host-versioned.

### 15. Always register a factory, never a singleton

Expose your renderer as a **factory function** — a zero-argument function the Host calls to get a
**fresh renderer instance every time** — on the global `window.feedBackViz_<id>` (where `<id>` is
your `plugin.json` `id`). Do **not** assign a single shared renderer object.

This is the whole reason splitscreen works: the Host creates one highway per panel and calls your
factory once per panel, so N panels get N independent renderers. A singleton would have every panel
fight over one WebGL context, one canvas, and one set of meshes — the classic splitscreen bug.

```js
function createRenderer() {
  // ALL state is per-instance closure state — one set per panel.
  let canvas, gl, meshes, unsubscribe;
  return {
    contextType: 'webgl2',                 // '2d' (default) or 'webgl2'; read before init()
    init(canvasEl, bundle) { canvas = canvasEl; /* acquire own context, build scene */ },
    draw(bundle) { /* render this frame from the snapshot */ },   // the only REQUIRED method
    resize(w, h) { /* rebuild framebuffers */ },
    destroy() { unsubscribe?.(); /* free GL + DOM */ },
  };
}
window.feedBackViz_my_viz = createRenderer;          // the global IS the factory function
window.feedBackViz_my_viz.contextType = 'webgl2';    // optional static, read before constructing
```

The renderer interface: `draw(bundle)` is **required**; `init(canvas, bundle)`, `resize(w, h)`,
`destroy()`, `contextType`, and `readyPromise` are optional. The Host lifecycle is
`factory()` → `init(canvas, bundle)` → per-frame `draw(bundle)` → `resize` on canvas change →
`destroy()` on renderer swap or stop.

### 16. Keep every resource per-instance and release it in `destroy()`

Hold your context, buffers, meshes, DOM overlays, and event subscriptions in the factory's closure,
one set per instance — never in module-level globals or a single shared DOM node parented to "the"
panel. `destroy()` runs on every swap and on stop and MUST release everything (unsubscribe, free GL,
remove any DOM you added); a leak here multiplies by the number of panels. Resolve any DOM against
**your own** instance's container, never a global `document.querySelector` that could grab a sibling
panel's node.

### 17. Treat the per-frame bundle as read-only, and keep `draw()` allocation-free

The `bundle` the Host passes to `draw()` is a **snapshot object reused across frames** — its array
fields are live, read-only references, not copies. Never mutate it, and never cache its identity or
its arrays across frames. Because `draw()` runs ~60 times a second **per panel**, do no allocation
and no DOM/layout work inside it (see rule 9) — precompute on `init`/`resize`.

### 18. Self-detect canvas size changes

Don't assume the Host will call your `resize()`. Under splitscreen the host may resize the highway
without forwarding the call to your renderer, so check the canvas's width/height at the top of
`draw()` against the last size you applied and rebuild your framebuffers when it drifts. (This was a
real bug where 3D highways stayed framed for their pre-fullscreen size in splitscreen.)

### 19. Communicate settings through `applySetting`, per instance — not a side channel

For user-adjustable controls, declare a `settings` array on your `visualization` capability
(`{ key, label, type: "toggle" | "range" | "select", default, min/max/step, options }`) and
implement **`applySetting(key, value)`** on the renderer instance. The Host validates the
descriptors, renders the controls, owns persistence, and calls `applySetting` **on each specific
per-panel instance** — so a change reaches every panel and is inherently per-instance, with no
shared global keys and no canvas-to-panel lookup to get wrong.

Hard-won rules this replaces — the ways settings communication actually broke:

- **Apply live; never reload.** Applying a setting via `location.reload()` reboots the app and drops
  the user out of the settings panel. Update the running renderer instead.
- **Don't let one setting leak into another.** If you migrate an old setting into a new one, back it
  up **once** on load and persist it *without* re-broadcasting; a "mirror on every read" makes one
  control silently overwrite another, and the render disagree with the UI.
- **Scope keys deliberately.** Only genuinely per-panel controls get per-panel storage; shared state
  (a palette, an uploaded asset) stays global, so a stale per-panel override can't shadow a global
  edit or duplicate a heavy asset per panel.
- **Reach every instance.** A settings change must fan out to all mounted panels, each re-reading in
  its own scope — not just the panel that happens to be focused.
- **The settings panel loads before your renderer.** `settings.html` is injected before your
  `script` runs, so guard any calls into your renderer's globals (`window.myViz && window.myViz…`)
  and let the panel hydrate its own controls from persisted values/defaults independently.

**On persistence and `localStorage`.** Under the `applySetting` contract the **Host owns
persistence** — declare the setting, apply values live, and let the Host store and replay them.
Prefer that: do **not** hand-roll settings into `localStorage`, which is what keeps export/import and
backups whole and stops per-panel copies from drifting. If your plugin nonetheless manages its own
persistence (a self-managed viz that predates the contract), two rules from the fixes apply:
`localStorage` is **synchronous and can throw** (quota / private mode), so stage the new value in an
in-memory fallback **before** the `setItem` and prefer that in-memory value on read — a failed write
must never leave the renderer showing a stale value while the UI claims the change applied. And
never touch `localStorage` on a per-frame path (rule 9) — read it once and cache it.

### 20. Fail safe — the Host reverts a broken renderer

If your `draw()` throws on several consecutive frames the Host automatically reverts to the built-in
renderer and emits a revert event. Guard `draw()` so a transient error degrades one frame rather
than tripping the auto-revert and dropping the user back to the default visualization.

---

## Shipping & good citizenship

### 21. Fail soft, log clearly

- Use `context["log"]` (server) so your messages land in the Host log under your plugin's
  namespace.
- A missing config file should mean "use defaults", not a crash. Read tolerantly (see the
  [full example](../examples/full-plugin/routes.py)).
- If a surface can't initialise, degrade to a reduced-but-working state rather than taking the
  whole plugin down.

### 22. Degrade gracefully across Host versions

A plugin may run on a Host older than the one you developed against. Don't assume a `context` key
or a client runtime API exists without a documented Host version guaranteeing it. If an optional
surface isn't supported, your plugin's other surfaces must still work.

### 23. Only declare capabilities you actually implement

`capabilities` and `standards` wire you into cross-plugin pipelines (diagnostics, capability
inspection). Declaring a capability you don't service registers a phantom participant and breaks
the pipeline. If you don't participate, omit both keys entirely.

### 24. Mind the security boundary

Your `routes` run arbitrary Python in the server process and your `script` runs in the app's
renderer. Validate every route input, don't shell out on user data, and don't reach outside your
plugin directory. Users installing your plugin are trusting it like an app extension — earn it.

### 25. Ship a README and a changelog

A plugin folder should carry a short `README.md` (what it does, which Host version it targets) and
note changes per version. It costs little and saves every future reader — including you.

---

## Checklist before you publish

- [ ] Folder name equals `id` exactly (incl. case), matching `^[a-z0-9][a-z0-9_-]*$`.
- [ ] `id` is specific and doesn't collide with a bundled plugin (a bundled `id` wins; yours would be
      silently ignored) or a reserved one (`capability_inspector`, `app_tour_*`).
- [ ] Global namespaces are prefixed by `id`: `localStorage` keys and any `window` globals. (Routes
      and CSS are covered separately below.)
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
- [ ] No synchronous `localStorage`, and no awaited `fetch`/network I/O, on a per-frame / per-note /
      gameplay-event path.
- [ ] Re-running `script` is a no-op (idempotent hydration) if you declare
      `plugin-runtime-idempotent.v1`.
- [ ] rAF loops and event subscriptions stop when the screen is hidden; state is per-instance.

**Visualizations (if `type` is `"visualization"`):**

- [ ] `window.feedBackViz_<id>` is a **factory function** returning a fresh renderer per call, not a
      shared object; all renderer state is per-instance closure state.
- [ ] `draw(bundle)` is implemented; the bundle is treated as read-only and never cached; `draw()`
      allocates nothing.
- [ ] `destroy()` releases every context/DOM/subscription; DOM is resolved against the instance's
      own container, not a global selector.
- [ ] Canvas size drift is self-detected in `draw()` (don't rely on `resize()` being called).
- [ ] Settings apply live via `applySetting(key, value)` on the instance (no reload, no cross-setting
      leakage, no shared global keys for per-panel controls).
- [ ] Persistence is left to the Host (no hand-rolled `localStorage`); if self-managed, writes are
      quota-safe (in-memory fallback staged before `setItem`) and never on a per-frame path.

**Capabilities & shipping:**

- [ ] Capabilities/standards declared only if actually implemented; cross-plugin calls go through
      `claim`/`dispatch`/`release`, not foreign globals.
- [ ] A `README.md` states purpose and target Host version.
