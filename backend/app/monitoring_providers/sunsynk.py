"""Sunsynk Connect API adapter. STUB — credentials required.

To enable:
  1. Set SUNSYNK_EMAIL and SUNSYNK_PASSWORD in env
  2. Run the polling worker (see docs/monitoring-worker.md — TODO)
  3. Register each client system in /monitoring with provider=sunsynk and its Sunsynk plant ID

Current behaviour: returns "unknown" so the framework stays usable in dev.
"""
from __future__ import annotations

import os
from typing import Any


name = "sunsynk"


def is_configured() -> bool:
    return bool(os.getenv("SUNSYNK_EMAIL") and os.getenv("SUNSYNK_PASSWORD"))


async def fetch_status(site: Any) -> dict:
    if not is_configured():
        return {"status": "unknown", "payload": {"note": "Sunsynk credentials not configured"}}
    # TODO: implement auth against https://api.sunsynk.net and pull plant summary
    return {"status": "unknown", "payload": {"note": "sunsynk adapter not yet implemented"}}
