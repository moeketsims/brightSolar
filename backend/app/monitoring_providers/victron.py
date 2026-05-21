"""Victron VRM API adapter. STUB — credentials required.

To enable:
  1. Set VICTRON_EMAIL and VICTRON_PASSWORD (or VICTRON_TOKEN) in env
  2. Register each site with provider=victron and its VRM site id
"""
from __future__ import annotations

import os
from typing import Any


name = "victron"


def is_configured() -> bool:
    return bool(os.getenv("VICTRON_TOKEN") or (os.getenv("VICTRON_EMAIL") and os.getenv("VICTRON_PASSWORD")))


async def fetch_status(site: Any) -> dict:
    if not is_configured():
        return {"status": "unknown", "payload": {"note": "Victron credentials not configured"}}
    # TODO: call https://vrmapi.victronenergy.com/v2/...
    return {"status": "unknown", "payload": {"note": "victron adapter not yet implemented"}}
