from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Vehicle
from app.schemas import VehicleCreate, VehicleOut

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Vehicle).order_by(Vehicle.name))
    return res.scalars().all()


@router.post("", response_model=VehicleOut, status_code=201)
async def create_vehicle(payload: VehicleCreate, session: AsyncSession = Depends(get_session)):
    v = Vehicle(**payload.model_dump())
    session.add(v)
    await session.commit()
    await session.refresh(v)
    return v


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(vehicle_id: int, payload: VehicleCreate, session: AsyncSession = Depends(get_session)):
    v = await session.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(404, "Vehicle not found")
    for k, val in payload.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    await session.commit()
    await session.refresh(v)
    return v


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(vehicle_id: int, session: AsyncSession = Depends(get_session)):
    v = await session.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(404, "Vehicle not found")
    await session.delete(v)
    await session.commit()
