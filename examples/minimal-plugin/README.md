# minimal-plugin

The smallest thing that loads: a directory named `minimal-plugin` containing a single
`plugin.json` with an `id`. It contributes no screen, settings, or routes — it just proves the
discovery contract (folder name == `id`).

Validate it:

```bash
python tools/validate.py examples/minimal-plugin
```
