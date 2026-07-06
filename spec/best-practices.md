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

## Minigames

A **minigame** is a plugin that registers a small, self-contained game into the bundled
`minigames` **host** — a hub + SDK that lists every registered game, runs one at a time, and owns
scoring and progression. You don't build a standalone game screen; you ship a normal plugin that
hands the host a *spec*, and the host mounts, runs, tears down, and scores it. As with the
visualization contract, the names below (`window.feedBackMinigames`, the `minigame` manifest block,
`spec.start`/`spec.stop`) are the **current Host contract** — treat the principles as stable and the
exact API as Host-versioned.

### 21. Register into the host — and bind late

The host loads **after** your plugin (plugins load alphabetically), so `window.feedBackMinigames`
usually does **not** exist yet when your `script` runs. Never assume it's there. Register through
the host's pending queue, which the host drains on init, and/or wait for its ready event:

```js
// Queue now; the host drains this when it initializes.
(window.__feedBackMinigamesPending ||= []).push(spec);
// Belt and braces: if the host is already up, or when it announces itself, register directly.
window.feedBackMinigames?.register(spec);
window.addEventListener('feedBack-minigames-ready',
  () => window.feedBackMinigames.register(spec), { once: true });
```

Registration is idempotent by `spec.id`, so queueing *and* handling the ready event registers once.

### 22. Declare a `minigame` manifest block; keep `spec.id` === plugin `id`

Put a `minigame` block in your `plugin.json` (display metadata — title, tagline, thumbnail,
modifiers) and register a runtime spec whose **`id` exactly equals your plugin `id`**. The host
treats the manifest as authoritative for display and the JS spec as the runtime behaviour; if the
two ids diverge, runs are misattributed and your manifest metadata is dropped. (This is the rule 2
`id` contract, applied to minigames.)

### 23. Implement `start`/`stop` — and release in `stop()` everything you create

Your spec provides `start({ container, modifiers, sdk })` (required) and `stop()`. Render your game
into the **`container` the host gives you**; drive input and scoring through the **`sdk`**. The host
tears your session down on navigation away mid-run (a `screen:changed`), and on teardown it cancels
**only its own** resources — its scheduler timers, the stage DOM, the summary listener. **Every
`requestAnimationFrame` loop, `AudioContext`, `getUserMedia` stream, timer, and listener *you* open
is yours to release in `stop()`.** The host cannot cancel a loop it never knew about, so anything
you forget leaks past the end of your game and keeps burning the main thread (see rule 9).

### 24. Make `start` supersede-safe

A user can double-tap a game tile, or navigate away while your `start` is still awaiting. Guard
against both: flip a synchronous "starting" flag on entry (don't rely on an async-set "active"
flag), and capture a start generation you re-check after every `await`, bailing if it changed. An
in-flight start that lost its race must not finish mounting or begin a run after teardown.

### 25. Be standalone by default; set `usesPlayer` only if you drive the highway

Minigames share the **guitar input**, not the song library or playback — a game is standalone by
default and is torn down on **any** screen change. Only if your game deliberately navigates to the
player screen and drives the note-highway itself should you mark it `usesPlayer`, which tells the
host not to tear you down for that one navigation. If you set it, you own your own
abandonment/cleanup for that hop.

### 26. Let the host score and persist; use the SDK for audio; expect one session

- **Report results, don't persist them.** End a run through the `sdk` your `start` received
  (`sdk.end({ score, durationMs, modifiers, meta })`); the host owns the runs database, the profile,
  and XP/progression, writes
  them atomically, and reconciles with the app's unified XP. Don't hand-roll a scores file. Keep
  `modifiers`/`meta` small (the host caps them).
- **Use the SDK's scoring/audio helpers** rather than opening your own microphone — on desktop the
  SDK pulls post-noise-gate frames from the native engine, where a naive `getUserMedia` would grab
  the wrong device.
- **Assume exactly one active session.** The host runs a single game at a time with singleton
  overlays; it does **not** support two concurrent minigame sessions (e.g. under splitscreen). Don't
  build a game that assumes it can run alongside another.

---

## Organizing client code across files

A plugin declares a single `script` (`screen.js`), but that doesn't force you into one giant file.
You can split your client code — you just have to work within how the Host loads and serves it.
The mechanics below are the current Host contract.

### 27. Prefer bundling to one `screen.js`; split at runtime only when you must

If you have any build tooling, author your plugin as many source files and **bundle them into the
one `screen.js` you ship**. The Host loads exactly one script, so a bundle sidesteps every gotcha in
the next two rules — no extra routes, no load-order or idempotency concerns. (feedBack ships no
bundler and serves plugin JS verbatim, so this is your own build step, not a Host feature — but it's
the simplest path to a non-monolithic plugin.)

If you split at runtime instead, know the constraint that shapes everything else: **`screen.js` runs
as a *classic* script, not an ES module.** Top-level `import` / `export` and `import.meta` do not
work in it. Split files therefore share state through **`window`** (namespaced under your `id`, per
rule 2), not through ES exports — each file attaches what it provides to a per-plugin object and
reads its dependencies from there. Key that object by `id` with **bracket notation**, since an `id`
may contain `-` (which isn't a valid JS identifier): `window['my-plugin']` or a shared
`(window.__feedBackPlugins ||= {})['my-plugin']` — not `window.my-plugin`, which is a syntax error.

### 28. Serve extra files from `assets/`, and reference them by absolute URL

The plugin **root is not a servable directory** — only `screen.js`, `screen.html`, `settings.html`,
`tour.json`, and everything under **`assets/`** are served. A helper at your plugin root
(`/api/plugins/<id>/lib/util.js`) returns 404; the same file under `assets/`
(`/api/plugins/<id>/assets/lib/util.js`) is served by the Host, path-traversal-guarded and with the
correct JavaScript MIME type. So put your split-out `.js` (and any `.css`, workers, or `.wasm`)
under `assets/`. (If you genuinely need a non-`assets/` layout, a `routes.py` can serve your own
sibling directories — but `assets/` is the built-in path and needs no server code.)

Reference these files by an **absolute** `/api/plugins/<id>/assets/…` URL, never a relative one.
Because `screen.js` is a classic script, a relative `import('./part.js')` resolves against the
document's base URL (the app root), not your script — so it silently hits the wrong path. Build a
base constant once and use it everywhere:

```js
const ASSET_BASE = '/api/plugins/my-plugin/assets/';   // hardcode your id
// screen.js is a classic script, so there's no top-level await — use .then (or an async IIFE):
import(ASSET_BASE + 'lib/util.js').then(util => { /* ES module served from assets/ */ });
// or a classic, window-attaching helper:
loadScriptOnce(ASSET_BASE + 'lib/legacy.js');          // see rule 29
```

Dynamic `import()` of a real ES module works this way (the module can use `import`/`export` among
*its own* files, addressed by absolute URL); classic `<script>` injection works for non-module
helpers that attach to `window`.

### 29. Load each split file exactly once

The Host may re-run your `screen.js` mid-session (rule 12), and your own screen may re-mount — so any
runtime loading must be **idempotent**. De-dupe it, but keep the cache **on `window`** (a module-local
`Set` is wiped when `screen.js` re-runs, so it wouldn't actually prevent a re-load), cache the
**in-flight promise** so concurrent callers share one load, and **drop the entry on failure** so a
transient error can be retried:

```js
const _loading = (window.__myPluginScripts ||= new Map());   // survives screen.js re-run
function loadScriptOnce(src) {
  let p = _loading.get(src);
  if (p) return p;                                            // resolved or in-flight — reuse
  p = new Promise((res, rej) => {
    const s = document.createElement('script');               // classic; attaches to window
    s.src = src; s.onload = res; s.onerror = rej;
    document.body.appendChild(s);
  }).catch(err => { _loading.delete(src); throw err; });      // allow retry after a failure
  _loading.set(src, p);
  return p;
}
```

---

## Integrating with the app

Beyond mounting a screen, most plugins need to *react to* and *drive* the app — react to the song
that's playing, navigate, control the transport. The Host exposes this through the `window.feedBack`
object; reach for it rather than the app's own DOM. (As with the rest of the client runtime surface,
these names are the current Host contract, versioned by the Host — feature-detect before you rely on
one.)

### 30. Subscribe to app state through the event bus

`window.feedBack` is an event bus: `on(event, fn)`, `off(event, fn)`, and `emit(event, detail)`. The
Host emits lifecycle events over it and you subscribe to react; the payload rides on `event.detail`.
The commonly-used events:

| Event | `event.detail` | Fires when |
|---|---|---|
| `screen:changed` | `{ id }` | The active screen changes (your screen becoming visible/hidden). |
| `song:loading` / `song:ready` | song info | A song starts loading / is ready to play. |
| `song:play` / `song:resume` / `song:pause` / `song:stop` / `song:ended` | — | Transport state changes. |
| `song:seek` / `song:position-changed` | `{ time, duration }` | The playhead moves. |
| `song:arrangement-changed` | arrangement | The user switches arrangement. |
| `library:changed` | `{ reason }` | The song library is rescanned/updated. |
| `viz:renderer:ready` / `viz:reverted` | `{ reason }` on revert | A visualization renderer starts / auto-reverts. |
| `highway:canvas-replaced` / `highway:visibility` | `{ … }` | The highway canvas is swapped / shown or hidden. |

Treat any event you don't recognise as optional (the set grows over time), keep handlers cheap (some
fire during playback — see rule 9), and **unsubscribe when your screen is hidden or torn down**
(rule 13) so a background plugin isn't doing work on every transport tick.

### 31. Drive the app through the `feedBack` API, not its DOM

To navigate, play, or control playback, call the Host API — never click or mutate the app's own
controls (`document.querySelector('#btn-loop-…')` and friends are private and move between UI
versions). The surface comes in two forms; **feature-detect** whichever one you call before relying
on it:

- **On the `window.feedBack` object:** `feedBack.navigate(screenId, params)` and
  `feedBack.getNavParams()`, `feedBack.seek(seconds, reason)`, `feedBack.setLoop(a, b)` /
  `feedBack.clearLoop()` / `feedBack.getLoop()`, and the live read-only state `feedBack.currentSong`
  / `feedBack.isPlaying`.
- **Legacy top-level globals** (supported but being migrated behind `feedBack`, per rule 32's
  caution about the surface): `window.showScreen(id)`, `window.playSong(...)`,
  `window.setReturnScreen(id)`, and the `window.feedBack.playQueue` queue API. Prefer the
  `feedBack`-namespaced call where one exists.

Going through the API keeps you working when the app's markup changes and avoids fighting the Host
for control of the transport.

### 32. Wrap Host functions carefully — call through, stay idempotent, clean up

A common pattern is wrapping a Host global like `playSong` or `showScreen` to run your own logic
around it. Do it defensively:

- **Always call — and `await` — the original.** Capture it, invoke it, return its result. Swallowing
  it breaks playback/navigation for the whole app and every other plugin in the wrapper chain.
- **Install the wrapper once.** Store it behind a stable singleton (rule 12) so re-hydration doesn't
  stack wrapper-on-wrapper.
- **Undo what a transition invalidates.** If you wrap `showScreen`, tear down your player-screen hooks
  when the user navigates away.
- **Don't assume load order.** Plugins load alphabetically, so a Host global or another plugin's API
  may not exist yet when your `script` runs — check for it at the moment you *use* it (or on the
  relevant event), not at load time.

### 33. Support both player UIs

feedBack has two player chromes (`v2` and `v3`). A plugin that injects controls into the player MUST
work in both: detect the active one (the Host exposes a `uiVersion` and a `v3` mount point such as
`ui.playerControlSlot()`), mount into the Host-provided slot rather than a hard-coded container, and
verify your plugin in **both** UIs before shipping. Don't rely on any backward-compatibility shim —
it's a migration aid, not a contract.

---

## Server-side robustness

Your `routes` module runs inside the Host's server process, sharing its event loop and startup
sequence with every other plugin. A slow or misbehaving plugin doesn't just hurt itself — it can
stall the server or delay every plugin that loads after it. These rules keep a backend plugin a good
tenant.

### 34. Declare Python dependencies in `requirements.txt` — and keep them light

A plugin's Python dependencies go in a **`requirements.txt`** file in the plugin directory (there is
no manifest field for this). On first load the Host `pip install`s them into a persistent location
and adds it to `sys.path`; the install is keyed by a hash of the file, so unchanged requirements
don't reinstall on later boots.

Two consequences shape good practice:

- **Installs are sequential and can be slow, and they delay *later* plugins.** While your deps
  install (potentially minutes) your plugin shows as "installing…", and plugins after you in load
  order wait their turn. Keep the dependency set **small**, prefer wheels, and **pin versions** for
  reproducibility. Don't pull a huge library for a small need.
- **A failed install is non-fatal — the Host still tries to load your routes.** So `import` a heavy
  or optional dependency **defensively** (guard it and degrade if it's missing) rather than assuming
  it installed; if a genuinely required dep fails, your routes import will fail and the Host shows
  your plugin as "failed" rather than crashing.

### 35. Don't block the event loop; keep `setup()` fast

The Host calls your `setup(app, context)` on the **server's event-loop thread**, and it is killed if
it takes too long (on the order of a minute). Do only wiring in `setup()` — register routes, read a
small config — and defer any heavy work (scanning, model loading, large I/O) to a background task or
the first request that needs it.

The same discipline applies to your handlers. An `async def` handler that performs **blocking** work
(synchronous file, network, or CPU-bound work) freezes the whole server for *every* request while it
runs. Either use non-blocking I/O in an `async def`, or write the handler as a **plain `def`** — the
Host runs synchronous handlers in a threadpool where blocking is safe.

### 36. Split `routes.py` with `load_sibling`, not bare imports

The Host puts each plugin's directory on `sys.path`, and Python caches modules by bare name in
`sys.modules` — so if two plugins each ship a top-level `util.py`, whichever loads first wins and the
other silently gets the wrong module. To split your server code across files, load your own modules
through **`context["load_sibling"]("name")`**, which imports them under a per-plugin namespace
(`plugin_<id>.<name>`) so they can't collide, and lets your siblings use relative imports
(`from .shared import x`). Don't mix a bare `import util` and `load_sibling("util")` for the same
file — that executes it twice and splits its module-level state.

### 37. Log through `context["log"]`, never `print()`

Use the logger the Host hands you in `context["log"]`. It carries the Host's correlation context and
lands in the rotated log stream under your plugin's namespace; `print()` bypasses both and is easy to
lose. (And, per rule 7, mount every route under `/api/plugins/<id>/…` — route paths aren't namespaced
for you, and a collision with the Host or another plugin is silent and, per rule 6, permanent.)

---

## Styling

The app's own compiled stylesheet only contains the utility classes the bundled code happens to use.
A plugin installed at runtime (from the plugin manager, a shared folder, the community) cannot rely
on it — any class the app doesn't already use simply won't exist, and the plugin renders unstyled.
So a plugin owns its own styling.

### 38. Ship your own compiled stylesheet via `styles`

Declare a `styles` entry pointing to a **compiled** CSS file (under `assets/`, per rule 28) and put
every class your screen needs in it. Don't assume a utility class exists just because the app uses a
similar one — especially arbitrary-value utilities like `w-[37px]` or `bg-slate-800/50`, which are
generated on demand and are almost never in the app's sheet. If you author with a utility framework,
run its build to produce your own sheet; ship the compiled output, not a config.

### 39. Build it to coexist — no global resets, no CDN, cache-busted

- **Turn off the global reset.** Build your stylesheet with the framework's base/preflight reset
  **disabled** (e.g. Tailwind's `corePlugins.preflight = false`). A plugin sheet that ships a full CSS
  reset re-styles the entire app, not just your screen.
- **Keep it scoped.** Scope selectors under your screen's root (rule 7) so your rules don't leak
  outward — the flip side of the reset rule.
- **Never load a runtime CSS engine or CDN.** Don't pull the Tailwind Play CDN or any in-browser
  CSS-in-JS/JIT: it's slow, it's unavailable offline (feedBack runs local-first), and it recompiles on
  the main thread. Compile ahead of time and ship the result.
- **Bump your `version` when the stylesheet changes.** The Host cache-busts your assets by plugin
  version, so a stale sheet keeps serving until you bump (rule 4).

---

## Shipping & good citizenship

### 40. Fail soft, log clearly

- Use `context["log"]` (server) so your messages land in the Host log under your plugin's
  namespace.
- A missing config file should mean "use defaults", not a crash. Read tolerantly (see the
  [full example](../examples/full-plugin/routes.py)).
- If a surface can't initialise, degrade to a reduced-but-working state rather than taking the
  whole plugin down.

### 41. Degrade gracefully across Host versions

A plugin may run on a Host older than the one you developed against. Don't assume a `context` key
or a client runtime API exists without a documented Host version guaranteeing it. If an optional
surface isn't supported, your plugin's other surfaces must still work.

### 42. Only declare capabilities you actually implement

`capabilities` and `standards` wire you into cross-plugin pipelines (diagnostics, capability
inspection). Declaring a capability you don't service registers a phantom participant and breaks
the pipeline. If you don't participate, omit both keys entirely.

### 43. Mind the security boundary

Your `routes` run arbitrary Python in the server process and your `script` runs in the app's
renderer. Validate every route input, don't shell out on user data, and don't reach outside your
plugin directory. Users installing your plugin are trusting it like an app extension — earn it.

### 44. Ship a README and a changelog

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

**Server-side robustness (if you ship `routes`):**

- [ ] Python deps are in `requirements.txt`, pinned and minimal; heavy/optional imports are guarded
      and degrade if missing.
- [ ] `setup()` only wires things (fast); no blocking work on the event loop — blocking handlers are
      plain `def`, not `async def`.
- [ ] Server code is split via `context["load_sibling"]`, not bare `import`, and routes are
      namespaced under `/api/plugins/<id>/`.
- [ ] Logging goes through `context["log"]`, never `print()`.

**Styling (if your screen has custom CSS):**

- [ ] A compiled stylesheet ships via `styles`, containing every class the screen uses (no reliance
      on the app's sheet).
- [ ] Built with the base/preflight reset off and selectors scoped to your screen; no Tailwind Play
      CDN or runtime CSS engine; `version` bumped when the sheet changes.

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

**Minigames (if you register into the `minigames` host):**

- [ ] Registration binds late (pending queue + `feedBack-minigames-ready`), never assuming
      `window.feedBackMinigames` exists at eval.
- [ ] A `minigame` manifest block is declared and `spec.id` === the plugin `id`.
- [ ] `stop()` releases every rAF loop, `AudioContext`, `getUserMedia` stream, timer, and listener
      the game opened; `start` is supersede-safe.
- [ ] Standalone by default (`usesPlayer` only if the game drives the highway); results reported via
      the SDK (host owns scoring/persistence); assumes a single active session.

**Split client code (if `screen.js` isn't a single bundle):**

- [ ] Extra JS lives under `assets/` (or a `routes.py`-served dir), not the plugin root, and is
      referenced by absolute `/api/plugins/<id>/…` URLs.
- [ ] Split files share state via a bracket-keyed `window["<id>"]` namespace (classic script — no
      `import`/`export` or top-level `await` in `screen.js`).
- [ ] Runtime loads are de-duped so re-hydration doesn't load them twice.

**Integrating with the app:**

- [ ] React to app state via the `window.feedBack` event bus; handlers are cheap and unsubscribe
      when hidden.
- [ ] Navigation/playback goes through the `feedBack` API (`navigate`, `playSong`, `setLoop`, …),
      never the app's own DOM controls.
- [ ] Any wrapped Host function calls + `await`s the original, installs once, and cleans up; no
      load-order assumptions.
- [ ] Player-injecting plugins work in both `v2` and `v3` (mount into the Host slot).

**Capabilities & shipping:**

- [ ] Capabilities/standards declared only if actually implemented; cross-plugin calls go through
      `claim`/`dispatch`/`release`, not foreign globals.
- [ ] A `README.md` states purpose and target Host version.
