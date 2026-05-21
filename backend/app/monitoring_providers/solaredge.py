"""SolarEdge monitoring API adapter. STUB — credentials required.

To enable:
  1. Generate a SolarEdge API key (one per installer account) and set SOLAREDGE_API_KEY
  2. Register each system in /monitoring with provider=solaredge and its site ID
"""
from __future__ import annotations

import os
from typing import Any


name = "solaredge"


def is_configured() -> bool:
    return bool(os.getenv("SOLAREDGE_API_KEY"))


async def fetch_status(site: Any) -> dict:
    if not is_configured():
        return {"status": "unknown", "payload": {"note": "SolarEdge API key not configured"}}
    # TODO: call https://monitoringapi.solaredge.com/site/{site}/overview
    return {"status": "unknown", "payload": {"note": "solaredge adapter not yet implemented"}}
