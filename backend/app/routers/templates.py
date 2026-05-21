from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Activity, Project, ServiceTemplate
from app.schemas import (
    ServiceTemplateCreate,
    ServiceTemplateOut,
    ServiceTemplateUpdate,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[ServiceTemplateOut])
async def list_templates(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(ServiceTemplate).order_by(ServiceTemplate.name))
    return res.scalars().all()


@router.post("", response_model=ServiceTemplateOut, status_code=201)
async def create_template(
    payload: ServiceTemplateCreate,
    session: AsyncSession = Depends(get_session),
):
    t = ServiceTemplate(
        name=payload.name,
        service_type=payload.service_type,
        description=payload.description,
        default_people_on_site=payload.default_people_on_site,
        default_estimated_hours_on_site=payload.default_estimated_hours_on_site,
        default_contingency_pct=payload.default_contingency_pct,
        default_margin_pct=payload.default_margin_pct,
        materials=[m.model_dump(mode="json") for m in payload.materials],
        activities=[a.model_dump(mode="json") for a in payload.activities],
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


@router.get("/{template_id}", response_model=ServiceTemplateOut)
async def get_template(template_id: int, session: AsyncSession = Depends(get_session)):
    t = await session.get(ServiceTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.patch("/{template_id}", response_model=ServiceTemplateOut)
async def update_template(
    template_id: int,
    payload: ServiceTemplateUpdate,
    session: AsyncSession = Depends(get_session),
):
    t = await session.get(ServiceTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    data = payload.model_dump(exclude_unset=True, mode="json")
    for k, v in data.items():
        setattr(t, k, v)
    await session.commit()
    await session.refresh(t)
    return t


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int, session: AsyncSession = Depends(get_session)):
    t = await session.get(ServiceTemplate, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    await session.delete(t)
    await session.commit()


@router.post("/from-project/{project_id}", response_model=ServiceTemplateOut, status_code=201)
async def save_from_project(
    project_id: int,
    name: str,
    session: AsyncSession = Depends(get_session),
):
    """Snapshot an existing project's shape as a new template."""
    res = await session.execute(
        select(Project)
        .options(selectinload(Project.activities))
        .where(Project.id == project_id)
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")

    activities = [
        {
            "title": a.title,
            "description": a.description,
            "estimated_hours": str(a.estimated_hours or 0),
            "position": a.position,
        }
        for a in sorted(p.activities, key=lambda x: x.position)
    ]
    t = ServiceTemplate(
        name=name,
        service_type=p.service_type,
        description=p.description,
        default_people_on_site=p.people_on_site,
        default_estimated_hours_on_site=p.estimated_hours_on_site,
        default_contingency_pct=p.contingency_pct,
        default_margin_pct=p.margin_pct,
        materials=p.materials or [],
        activities=activities,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t
