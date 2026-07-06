# feedBack plugin best practices

Practical, non-normative guidance for building good feedBack plugins. The
[specification](plugin-spec-v1.md) is the contract — what a plugin *must* do to load. This guide
is the advice — what a plugin *should* do to be a good citizen. Nothing here overrides the spec.

If you are writing your first plugin, start from [`examples/minimal-plugin`](../examples/minimal-plugin)
and grow it toward [`examples/full-plugin`](../examples/full-plugin).

---

## 1. Start from the smallest thing that loads

The smallest valid plugin is a folder with one file:

```text
my-plugin/
└── plugin.json      →  {"id": "my-plugin", "name": "My Plugin"}
```

Get *that* discovered first (folder name equal to `id`, dropped into a plugins directory), then
add one surface at a time — a screen, then settings, then routes. Adding surfaces incrementally
means when something stops loading you know exactly which change caused it.

## 2. Treat the `id` as forever

The `id` keys your settings store, your routes namespace, and your capability declarations.
Renaming it silently orphans every user's saved settings. Pick a lowercase, `-`/`_`-separated,
descriptive `id` once (`drum_highway_3d`, not `dh3` or `DrumHighway`) and never change it. The
folder name must match it exactly.

## 3. Keep the manifest declarative

Every file your plugin uses at load time should be *pointed at* from the manifest — `script`,
`screen`, `styles`, `settings.html`, `routes`, `tour`. If the Host has to guess a filename, a
future Host change can break you. Conversely, don't reference files you don't ship.

## 4. Version your plugin with semver

Set `version` and bump it on every release: PATCH for fixes, MINOR for new optional behaviour,
MAJOR when you change or remove behaviour users depend on. The plugin manager uses it to detect
updates, and users use it to report bugs against a known build.

## 5. Server routes: do nothing at import time

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

## 6. Register routes only after you've validated

The Host may be unable to *un*-register a route once mounted. So validate configuration, open
files, and check inputs **before** the first `app.get(...)` / `app.post(...)`. A `setup()` that
mounts two routes and then throws leaves two half-working endpoints behind permanently.

## 7. Namespace everything under your `id`

- Routes: `"/api/plugin/my-plugin/state"`, not `"/state"`.
- CSS: scope selectors to your screen's root element, don't style bare `body`/`h1`.
- Persisted files: write under the `config_dir` the Host hands you, in a file named for your
  plugin (`config_dir / "my_plugin.json"`).

Collisions with the Host or another plugin are silent and maddening; namespacing prevents them.

## 8. Persist state where the Host tells you

Read and write only inside `context["config_dir"]` and any paths you declared in
`settings.server_files`. Never write elsewhere in the Host's config/data tree, and never read
another plugin's files. This is what keeps export/import, backups, and uninstall clean.

## 9. Fail soft, log clearly

- Use `context["log"]` so your messages land in the Host log under your plugin's namespace.
- A missing config file should mean "use defaults", not a crash. Read tolerantly (see the
  [full example](../examples/full-plugin/routes.py)).
- If a surface can't initialise, degrade to a reduced-but-working state rather than taking the
  whole plugin down.

## 10. Degrade gracefully across Host versions

A plugin may run on a Host older than the one you developed against. Don't assume a `context` key
or a client runtime API exists without a documented Host version guaranteeing it. If an optional
surface isn't supported, your plugin's other surfaces must still work.

## 11. Only declare capabilities you actually implement

`capabilities` and `standards` wire you into cross-plugin pipelines (diagnostics, capability
inspection). Declaring a capability you don't service registers a phantom participant and breaks
the pipeline. If you don't participate, omit both keys entirely.

## 12. Mind the security boundary

Your `routes` run arbitrary Python in the server process and your `script` runs in the app's
renderer. Validate every route input, don't shell out on user data, and don't reach outside your
plugin directory. Users installing your plugin are trusting it like an app extension — earn it.

## 13. Ship a README and a changelog

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
- [ ] Capabilities/standards declared only if actually implemented.
- [ ] A `README.md` states purpose and target Host version.
