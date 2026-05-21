"""Remote monitoring framework — manages a roster of client systems and their
last-known status. The provider-specific fetch logic (Sunsynk, SolarEdge, Victron
APIs) lives in ``app/monitoring_providers/`` as plugins. Each provider class
implements ``fetch_status(site) -> {status, payload}``. No real providers wired
until their API credentials are configured in env.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Client, MonitoringProvider, MonitoringSite

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class SiteBase(BaseModel):
    client_id: int
    project_id: int | None = None
    provider: MonitoringProvider
    provider_site_id: str
    system_label: str
    notes: str | None = None
    active: bool = True


class SiteCreate(SiteBase):
    pass


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    last_status: str | None
    last_checked_at: datetime | None
    last_payload: dict | None
    created_at: datetime


class SiteStatusUpdate(BaseModel):
    """Written by the polling worker after it queries the provider."""
    status: str
    payload: dict


@router.get("", response_model=list[SiteOut])
async def list_sites(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(MonitoringSite).order_by(MonitoringSite.system_label))
    return res.scalars().all()


@router.post("", response_model=SiteOut, status_code=201)
async def register_site(payload: SiteCreate, session: AsyncSession = Depends(get_session)):
    client = await session.get(Client, payload.client_id)
    if not client:
        raise HTTPException(400, "Client not found")
    site = MonitoringSite(**payload.model_dump())
    session.add(site)
    await session.commit()
    await session.refresh(site)
    return site


@router.patch("/{site_id}/status", response_model=SiteOut)
async def update_status(
    site_id: int,
    payload: SiteStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Polling worker calls this with whatever it fetched from the provider."""
    site = await session.get(MonitoringSite, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    site.last_status = payload.status
    site.last_payload = payload.payload
    site.last_checked_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(site)
    return site


@router.delete("/{site_id}", status_code=204)
async def delete_site(site_id: int, session: AsyncSession = Depends(get_session)):
    site = await session.get(MonitoringSite, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    await session.delete(site)
    await session.commit()
