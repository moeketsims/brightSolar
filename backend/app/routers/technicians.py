from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Technician
from app.schemas import TechnicianCreate, TechnicianOut

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("", response_model=list[TechnicianOut])
async def list_technicians(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Technician).order_by(Technician.name))
    return res.scalars().all()


@router.post("", response_model=TechnicianOut, status_code=201)
async def create_technician(payload: TechnicianCreate, session: AsyncSession = Depends(get_session)):
    t = Technician(**payload.model_dump())
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


@router.patch("/{tech_id}", response_model=TechnicianOut)
async def update_technician(tech_id: int, payload: TechnicianCreate, session: AsyncSession = Depends(get_session)):
    t = await session.get(Technician, tech_id)
    if not t:
        raise HTTPException(404, "Technician not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await session.commit()
    await session.refresh(t)
    return t


@router.delete("/{tech_id}", status_code=204)
async def delete_technician(tech_id: int, session: AsyncSession = Depends(get_session)):
    t = await session.get(Technician, tech_id)
    if not t:
        raise HTTPException(404, "Technician not found")
    await session.delete(t)
    await session.commit()
