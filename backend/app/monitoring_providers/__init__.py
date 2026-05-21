"""Provider adapters for remote monitoring systems.

Each provider implements a simple interface:

    class Provider:
        name: str
        async def fetch_status(site) -> dict:  # returns {"status": "ok|warning|fault|offline", "payload": {...}}

Real adapters (Sunsynk, SolarEdge, Victron) require vendor API credentials; until
those are configured in env, the dispatcher skips them. This keeps the integration
pluggable so you can add a vendor by dropping a new module here without changing
the core app.
"""
from __future__ import annotations
