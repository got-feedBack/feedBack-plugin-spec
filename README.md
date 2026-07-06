# feedBack plugin specification

The specification and best-practices guide for building **plugins** for feedBack. A plugin is a
self-contained folder — described entirely by its `plugin.json` manifest — that extends feedBack
with a screen, a settings panel, server routes, and/or a declared capability.

- 🌐 **Rendered site & hosted schema:** <https://got-feedback.github.io/feedBack-plugin-spec/>
- 📖 **Read the spec:** [`spec/plugin-spec-v1.md`](spec/plugin-spec-v1.md)
- ✅ **Best-practices guide:** [`spec/best-practices.md`](spec/best-practices.md)
- 🧩 **Machine-readable schema:** [`schemas/plugin.schema.json`](schemas/plugin.schema.json) (JSON Schema, Draft 2020-12)
- 📦 **Worked examples:** [`examples/`](examples/)
- 🔎 **Reference validator:** [`tools/validate.py`](tools/validate.py)

| | |
|---|---|
| **Specification version** | 1.0.0 |
| **Manifest major version** | 1 |
| **Status** | Stable |
| **Manifest file** | `plugin.json` |

## What a plugin looks like

A plugin is a directory whose name equals its `id`. Only `plugin.json` is required; every other
file exists because the manifest points at it.

```text
tuner/                     # directory name == manifest "id"
├── plugin.json            # the manifest (required)
├── screen.js              # client script      (manifest "script")
├── settings.html          # settings panel      (manifest "settings.html")
├── routes.py              # server routes       (manifest "routes")
├── assets/plugin.css      # styles              (manifest "styles")
└── tour.json              # guided tour         (manifest "tour")
```

The design rests on three ideas, spelled out in the spec:

1. **The manifest is the contract.** A plugin is discovered and described entirely by its
   `plugin.json`; nothing is inferred from files the manifest doesn't declare.
2. **A plugin is a folder, identified by its `id`.** The directory name MUST equal the manifest
   `id` — that is the whole discovery rule.
3. **Optional surfaces, loaded independently.** Screen, settings, routes, tour, and capabilities
   each load only if declared, and a failure in one doesn't take down the others.

## Validate a plugin

```bash
pip install jsonschema
python tools/validate.py path/to/my-plugin
python tools/validate.py examples/minimal-plugin examples/full-plugin
```

The validator is also a minimal reference implementation of the discovery contract: it schema-
checks `plugin.json`, enforces that the directory name equals the `id`, and confirms every file
the manifest references exists.

## Versioning

Three version axes are kept separate (see [spec §9](spec/plugin-spec-v1.md#9-versioning-and-compatibility)):

- **Specification-document version** — this published document, frozen per release with a git tag.
- **Manifest major version** — the shape of `plugin.json` (currently `1`).
- **A plugin's own `version`** — independent of both of the above.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q                       # validator unit tests
python -m ruff check tools/ tests/
python tools/validate.py examples/minimal-plugin examples/full-plugin
```

CI (`.github/workflows/validate.yml`) meta-checks the schema, validates the example plugins, runs
the tests across Python 3.10–3.13, lints, checks that the spec/README/CHANGELOG versions agree,
and builds the docs site. On every push to `main` the docs are published to GitHub Pages and a
GitHub Release is cut for the newest `CHANGELOG.md` version if it doesn't already exist — so a
reviewed version bump releases itself on merge.

## License

This repository is licensed under [**AGPL-3.0-only**](LICENSE), consistent with the feedBack
application and server. See [CONTRIBUTING.md](CONTRIBUTING.md) for the DCO sign-off requirement.

## Contributing

Proposals to evolve the plugin format are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
enhancement-proposal process and DCO sign-off, and [GOVERNANCE.md](GOVERNANCE.md) for how versions
are decided and cut. Changes are tracked in [CHANGELOG.md](CHANGELOG.md).
