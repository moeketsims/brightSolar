import csv
import io
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Trip, Vehicle

router = APIRouter(tags=["trips"])


class TripBase(BaseModel):
    vehicle_id: int
    project_id: int | None = None
    trip_date: date
    from_location: str
    to_location: str
    purpose: str
    odo_start: int | None = None
    odo_end: int | None = None
    business_km: Decimal | None = None
    technician_id: int | None = None
    notes: str | None = None


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    trip_date: date | None = None
    from_location: str | None = None
    to_location: str | None = None
    purpose: str | None = None
    odo_start: int | None = None
    odo_end: int | None = None
    business_km: Decimal | None = None
    technician_id: int | None = None
    notes: str | None = None


class TripOut(TripBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_name: str | None = None
    project_title: str | None = None


def _computed_km(payload: TripBase | TripUpdate, existing_odo_start: int | None = None, existing_odo_end: int | None = None) -> Decimal:
    start = payload.odo_start if payload.odo_start is not None else existing_odo_start
    end = payload.odo_end if payload.odo_end is not None else existing_odo_end
    if payload.business_km is not None:
        return Decimal(payload.business_km)
    if start is not None and end is not None and end >= start:
        return Decimal(end - start)
    return Decimal("0")


@router.get("/trips", response_model=list[TripOut])
async def list_trips(
    vehicle_id: int | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Trip)
        .options(selectinload(Trip.vehicle), selectinload(Trip.project))
        .order_by(Trip.trip_date.desc(), Trip.id.desc())
    )
    if vehicle_id is not None:
        stmt = stmt.where(Trip.vehicle_id == vehicle_id)
    if from_date is not None:
        stmt = stmt.where(Trip.trip_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Trip.trip_date <= to_date)
    res = await session.execute(stmt)
    trips = res.scalars().all()
    return [
        TripOut(
            id=t.id,
            vehicle_id=t.vehicle_id,
            project_id=t.project_id,
            trip_date=t.trip_date,
            from_location=t.from_location,
            to_location=t.to_location,
            purpose=t.purpose,
            odo_start=t.odo_start,
            odo_end=t.odo_end,
            business_km=t.business_km,
            technician_id=t.technician_id,
            notes=t.notes,
            vehicle_name=t.vehicle.name if t.vehicle else None,
            project_title=t.project.title if t.project else None,
        )
        for t in trips
    ]


@router.post("/trips", response_model=TripOut, status_code=201)
async def create_trip(payload: TripCreate, session: AsyncSession = Depends(get_session)):
    vehicle = await session.get(Vehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(400, "Vehicle not found")
    km = _computed_km(payload)
    t = Trip(**payload.model_dump(), )
    t.business_km = km
    session.add(t)
    await session.commit()
    await session.refresh(t, attribute_names=["vehicle", "project"])
    return TripOut(
        id=t.id,
        vehicle_id=t.vehicle_id,
        project_id=t.project_id,
        trip_date=t.trip_date,
        from_location=t.from_location,
        to_location=t.to_location,
        purpose=t.purpose,
        odo_start=t.odo_start,
        odo_end=t.odo_end,
        business_km=t.business_km,
        technician_id=t.technician_id,
        notes=t.notes,
        vehicle_name=t.vehicle.name if t.vehicle else None,
        project_title=t.project.title if t.project else None,
    )


@router.patch("/trips/{trip_id}", response_model=TripOut)
async def update_trip(trip_id: int, payload: TripUpdate, session: AsyncSession = Depends(get_session)):
    t = await session.get(Trip, trip_id)
    if not t:
        raise HTTPException(404, "Trip not found")
    data = payload.model_dump(exclude_unset=True, mode="json")
    for k, v in data.items():
        setattr(t, k, v)
    # Recompute km if odo changed
    t.business_km = _computed_km(payload, t.odo_start, t.odo_end)
    await session.commit()
    await session.refresh(t, attribute_names=["vehicle", "project"])
    return TripOut(
        id=t.id,
        vehicle_id=t.vehicle_id,
        project_id=t.project_id,
        trip_date=t.trip_date,
        from_location=t.from_location,
        to_location=t.to_location,
        purpose=t.purpose,
        odo_start=t.odo_start,
        odo_end=t.odo_end,
        business_km=t.business_km,
        technician_id=t.technician_id,
        notes=t.notes,
        vehicle_name=t.vehicle.name if t.vehicle else None,
        project_title=t.project.title if t.project else None,
    )


@router.delete("/trips/{trip_id}", status_code=204)
async def delete_trip(trip_id: int, session: AsyncSession = Depends(get_session)):
    t = await session.get(Trip, trip_id)
    if not t:
        raise HTTPException(404, "Trip not found")
    await session.delete(t)
    await session.commit()


@router.get("/trips/export.csv")
async def export_trips(
    vehicle_id: int | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """SARS-compliant CSV export. Columns match the typical SARS travel logbook fields."""
    stmt = select(Trip).options(selectinload(Trip.vehicle)).order_by(Trip.trip_date)
    if vehicle_id is not None:
        stmt = stmt.where(Trip.vehicle_id == vehicle_id)
    if from_date is not None:
        stmt = stmt.where(Trip.trip_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Trip.trip_date <= to_date)
    res = await session.execute(stmt)
    trips = res.scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "Date",
        "Vehicle",
        "Registration",
        "From",
        "To",
        "Purpose of trip (business reason)",
        "Odometer start",
        "Odometer end",
        "Business km",
    ])
    for t in trips:
        v = t.vehicle
        w.writerow([
            t.trip_date.isoformat(),
            v.name if v else "",
            v.registration if v else "",
            t.from_location,
            t.to_location,
            t.purpose,
            t.odo_start or "",
            t.odo_end or "",
            f"{t.business_km:.2f}",
        ])

    filename = "sars-travel-logbook.csv"
    if vehicle_id:
        vehicle = await session.get(Vehicle, vehicle_id)
        if vehicle:
            filename = f"sars-logbook-{vehicle.name.replace(' ', '_')}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
