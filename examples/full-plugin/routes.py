"""Server routes for the full-plugin example.

Demonstrates the spec's server-surface guidance (spec §7):
  * all work happens inside setup() — nothing at import time;
  * config is read tolerantly (missing file => defaults);
  * routes are namespaced under the plugin id;
  * setup() validates before registering any route.
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PLUGIN_ID = "full-plugin"
_DEFAULTS = {"color": "indigo", "intensity": 5}


def setup(app: FastAPI, context: dict) -> None:
    config_dir = Path(context["config_dir"])
    log = context.get("log") or logging.getLogger(f"feedBack.plugin.{PLUGIN_ID}")
    config_file = config_dir / f"{PLUGIN_ID}.json"

    def _read() -> dict:
        """Read persisted settings, tolerating a missing or corrupt file."""
        if not config_file.exists():
            return dict(_DEFAULTS)
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            return {**_DEFAULTS, **data} if isinstance(data, dict) else dict(_DEFAULTS)
        except (OSError, ValueError) as exc:
            log.warning("%s: unreadable config, using defaults: %s", PLUGIN_ID, exc)
            return dict(_DEFAULTS)

    # Everything below only runs after the plugin has validated its own state.
    @app.get(f"/api/plugins/{PLUGIN_ID}/settings")
    def get_settings() -> JSONResponse:
        return JSONResponse(_read())

    @app.post(f"/api/plugins/{PLUGIN_ID}/settings")
    async def set_settings(request: Request) -> JSONResponse:
        incoming = await request.json()
        if not isinstance(incoming, dict):
            return JSONResponse({"error": "body must be an object"}, status_code=400)
        merged = {**_read(), **incoming}
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        return JSONResponse(merged)

    log.info("%s routes registered", PLUGIN_ID)
