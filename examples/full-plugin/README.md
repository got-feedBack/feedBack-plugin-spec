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
mount lifecycle is described in [§6.1](../../spec/plugin-spec-v1.md#61-screen-mount-lifecycle) and
the Host-provided (and Host-versioned) runtime surface in
[§6.3](../../spec/plugin-spec-v1.md#63-the-client-runtime-surface); the portable performance rules
are normative in [§6.4](../../spec/plugin-spec-v1.md#64-performance-and-the-shared-main-thread).
