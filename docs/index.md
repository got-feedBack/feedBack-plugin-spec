# feedBack plugin specification

The specification and best-practices guide for building **plugins** for feedBack. A plugin is a
self-contained folder — described entirely by its `plugin.json` manifest — that extends feedBack
with a screen, a settings panel, server routes, and/or a declared capability.

[Read the specification](plugin-spec-v1.md){ .md-button .md-button--primary }
[Best-practices guide](best-practices.md){ .md-button }

## Documents

- [Specification](plugin-spec-v1.md) — the authoritative, normative reference: the manifest,
  discovery and loading, the client and server surfaces, capabilities, and versioning.
- [Best-practices guide](best-practices.md) — non-normative advice for building good plugins.
- [Changelog](changelog.md) — version history.

## Machine-readable schema

JSON Schema (Draft 2020-12) for the manifest — the resolvable counterpart of the manifest
reference:

- [plugin.schema.json](schemas/plugin.schema.json)

## Worked examples

- `examples/minimal-plugin` — the smallest thing that loads (manifest only).
- `examples/full-plugin` — every surface: screen, styles, settings, routes, capabilities.

Validate any plugin against the schema and the structural rules:

```bash
pip install jsonschema
python tools/validate.py path/to/my-plugin
```

## License

This repository is licensed under
[AGPL-3.0-only](https://github.com/got-feedback/feedBack-plugin-spec/blob/main/LICENSE),
consistent with the feedBack application and server.
