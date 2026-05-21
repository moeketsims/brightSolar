from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import (
    Project,
    ProjectEvent,
    ProjectEventKind,
    VariationOrder,
)
from app.routers.settings import get_or_create_settings

router = APIRouter(tags=["variations"])


class VariationCreate(BaseModel):
    scope_delta: str
    cost_delta_ex_vat: Decimal
    reason: str | None = None


class VariationAccept(BaseModel):
    accepted_by_name: str


class VariationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    vo_number: str
    scope_delta: str
    cost_delta_ex_vat: Decimal
    vat_pct_snapshot: Decimal
    reason: str | None
    accepted_at: datetime | None
    accepted_by_name: str | None
    created_at: datetime


def _next_vo_number(existing_numbers: list[str]) -> str:
    max_seq = 0
    for n in existing_numbers:
        if n and n.startswith("BSP-VO-"):
            try:
                seq = int(n.split("-")[-1])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass
    return f"BSP-VO-{max_seq + 1:04d}"


@router.get("/projects/{project_id}/variations", response_model=list[VariationOut])
async def list_variations(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(VariationOrder).where(VariationOrder.project_id == project_id).order_by(VariationOrder.id)
    )
    return res.scalars().all()


@router.post("/projects/{project_id}/variations", response_model=VariationOut, status_code=201)
async def create_variation(
    project_id: int,
    payload: VariationCreate,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    nums = await session.execute(select(VariationOrder.vo_number))
    vo_number = _next_vo_number([n for (n,) in nums.all()])
    vo = VariationOrder(
        project_id=project_id,
        vo_number=vo_number,
        scope_delta=payload.scope_delta,
        cost_delta_ex_vat=payload.cost_delta_ex_vat,
        vat_pct_snapshot=Decimal(project.vat_pct or 15),
        reason=payload.reason,
    )
    session.add(vo)
    total_delta_inc_vat = Decimal(payload.cost_delta_ex_vat) * (Decimal("1") + Decimal(project.vat_pct or 15) / Decimal("100"))
    session.add(
        ProjectEvent(
            project_id=project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"Variation order {vo_number} drafted — {payload.scope_delta[:80]} ({'+' if payload.cost_delta_ex_vat >= 0 else ''}R{total_delta_inc_vat:,.2f} inc VAT)",
            details=payload.reason,
        )
    )
    await session.commit()
    await session.refresh(vo)
    return vo


@router.post("/variations/{variation_id}/accept", response_model=VariationOut)
async def accept_variation(
    variation_id: int,
    payload: VariationAccept,
    session: AsyncSession = Depends(get_session),
):
    vo = await session.get(VariationOrder, variation_id)
    if not vo:
        raise HTTPException(404, "Variation not found")
    if vo.accepted_at:
        raise HTTPException(409, "Already accepted")
    vo.accepted_at = datetime.now(timezone.utc)
    vo.accepted_by_name = payload.accepted_by_name.strip()
    session.add(
        ProjectEvent(
            project_id=vo.project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"Variation order {vo.vo_number} accepted by {vo.accepted_by_name}",
        )
    )
    await session.commit()
    await session.refresh(vo)
    return vo


@router.delete("/variations/{variation_id}", status_code=204)
async def delete_variation(variation_id: int, session: AsyncSession = Depends(get_session)):
    vo = await session.get(VariationOrder, variation_id)
    if not vo:
        raise HTTPException(404, "Variation not found")
    if vo.accepted_at:
        raise HTTPException(409, "Cannot delete an accepted variation order")
    await session.delete(vo)
    await session.commit()


@router.get("/variations/{variation_id}/pdf")
async def variation_pdf(variation_id: int, session: AsyncSession = Depends(get_session)):
    from app.pdf import render_variation_pdf

    res = await session.execute(
        select(VariationOrder)
        .options(selectinload(VariationOrder.project).selectinload(Project.client))
        .where(VariationOrder.id == variation_id)
    )
    vo = res.scalar_one_or_none()
    if not vo:
        raise HTTPException(404, "Variation not found")
    settings_row = await get_or_create_settings(session)
    pdf_bytes = render_variation_pdf(vo, vo.project, settings_row)
    safe = "".join(c for c in vo.project.client.name if c.isalnum() or c in (" ", "-")).strip()[:30] or "client"
    filename = f"{vo.vo_number}-{safe.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
