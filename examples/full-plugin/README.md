# full-plugin

A worked example that exercises every plugin surface described in the
[specification](../../spec/plugin-spec-v1.md):

| Surface | File | Manifest key |
|---|---|---|
| Client screen | `screen.js` | `script` |
| Styles | `assets/plugin.css` | `styles` |
| Settings panel | `settings.html` | `settings.html` |
| Server routes | `routes.py` | `routes` |
| Capabilities | — | `capabilities` |

Every file is referenced from `plugin.json`; every referenced file is present. That is exactly
what the validator checks:

```bash
python tools/validate.py examples/full-plugin
```

Target Host: written against the plugin runtime documented for feedBack as of spec v0.1.0. The
client runtime API (how `screen.js` mounts) is Host-provided and not yet pinned by the spec — see
[§6.1](../../spec/plugin-spec-v1.md#61-screen).
