from datetime import date as date_cls, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import (
    Activity,
    ActivityStatus,
    Project,
    ProjectEvent,
    ProjectEventKind,
    TimeEntry,
    Technician,
)
from app.schemas import (
    ActivityCreate,
    ActivityOut,
    ActivityStartIn,
    ActivityStopIn,
    ActivityUpdate,
    TimeEntryOut,
    TodayActivity,
    TodayBoard,
    TodayTechColumn,
)

router = APIRouter(tags=["activities"])


def _actual_hours(act: Activity) -> Decimal:
    """Sum closed time entries + any open entry (treated as running clock)."""
    total = Decimal("0")
    now = datetime.now(timezone.utc)
    for te in act.time_entries:
        if te.hours is not None:
            total += Decimal(te.hours)
        elif te.ended_at is None:
            elapsed = (now - te.started_at).total_seconds() / 3600.0
            if elapsed > 0:
                total += Decimal(str(round(elapsed, 2)))
    return total.quantize(Decimal("0.01"))


async def _load_tech_names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    res = await session.execute(select(Technician).where(Technician.id.in_(ids)))
    return {t.id: t.name for t in res.scalars().all()}


def _time_entries_out(entries: list[TimeEntry], names: dict[int, str]) -> list[TimeEntryOut]:
    out: list[TimeEntryOut] = []
    for te in entries:
        out.append(
            TimeEntryOut(
                id=te.id,
                activity_id=te.activity_id,
                technician_id=te.technician_id,
                technician_name=names.get(te.technician_id),
                started_at=te.started_at,
                ended_at=te.ended_at,
                hours=te.hours,
                note=te.note,
            )
        )
    return out


async def _to_out(session: AsyncSession, act: Activity) -> ActivityOut:
    tech_ids = set([tid for tid in (act.assigned_tech_ids or [])])
    tech_ids.update(te.technician_id for te in act.time_entries)
    names = await _load_tech_names(session, tech_ids)
    return ActivityOut(
        id=act.id,
        project_id=act.project_id,
        title=act.title,
        description=act.description,
        status=act.status,
        estimated_hours=act.estimated_hours,
        scheduled_date=act.scheduled_date,
        due_date=act.due_date,
        blocker_reason=act.blocker_reason,
        notes=act.notes,
        assigned_tech_ids=act.assigned_tech_ids or [],
        position=act.position,
        started_at=act.started_at,
        completed_at=act.completed_at,
        actual_hours=_actual_hours(act),
        time_entries=_time_entries_out(act.time_entries, names),
        created_at=act.created_at,
        updated_at=act.updated_at,
    )


@router.get("/projects/{project_id}/activities", response_model=list[ActivityOut])
async def list_activities(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Activity)
        .options(selectinload(Activity.time_entries))
        .where(Activity.project_id == project_id)
        .order_by(Activity.position, Activity.id)
    )
    return [await _to_out(session, a) for a in res.scalars().all()]


@router.post("/projects/{project_id}/activities", response_model=ActivityOut, status_code=201)
async def create_activity(
    project_id: int,
    payload: ActivityCreate,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Determine next position
    existing = await session.execute(
        select(Activity.position).where(Activity.project_id == project_id)
    )
    positions = [p for p in existing.scalars().all()]
    next_pos = (max(positions) + 1) if positions else 0

    act = Activity(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        estimated_hours=payload.estimated_hours,
        scheduled_date=payload.scheduled_date,
        due_date=payload.due_date,
        blocker_reason=payload.blocker_reason,
        notes=payload.notes,
        assigned_tech_ids=payload.assigned_tech_ids,
        position=payload.position or next_pos,
    )
    session.add(act)
    session.add(
        ProjectEvent(
            project_id=project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"Activity added: {payload.title}",
        )
    )
    await session.commit()

    # Re-load with time_entries relationship
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == act.id)
    )
    return await _to_out(session, res.scalar_one())


@router.patch("/activities/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    act = res.scalar_one_or_none()
    if not act:
        raise HTTPException(404, "Activity not found")

    data = payload.model_dump(exclude_unset=True, mode="json")
    before_status = act.status

    for k, v in data.items():
        setattr(act, k, v)

    # Status transitions handle completed_at / started_at
    if "status" in data:
        if data["status"] == "done":
            if not act.completed_at:
                act.completed_at = datetime.now(timezone.utc)
        elif data["status"] == "in_progress" and not act.started_at:
            act.started_at = datetime.now(timezone.utc)
        elif data["status"] != "done":
            act.completed_at = None

    if before_status != act.status:
        session.add(
            ProjectEvent(
                project_id=act.project_id,
                kind=ProjectEventKind.SCOPE_CHANGED,
                summary=f"Activity '{act.title}': {before_status.value if hasattr(before_status, 'value') else before_status} → {act.status.value if hasattr(act.status, 'value') else act.status}",
            )
        )

    await session.commit()
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    return await _to_out(session, res.scalar_one())


@router.delete("/activities/{activity_id}", status_code=204)
async def delete_activity(activity_id: int, session: AsyncSession = Depends(get_session)):
    act = await session.get(Activity, activity_id)
    if not act:
        raise HTTPException(404, "Activity not found")
    title = act.title
    project_id = act.project_id
    await session.delete(act)
    session.add(
        ProjectEvent(
            project_id=project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"Activity removed: {title}",
        )
    )
    await session.commit()


@router.post("/activities/{activity_id}/start", response_model=ActivityOut)
async def start_activity(
    activity_id: int,
    payload: ActivityStartIn,
    session: AsyncSession = Depends(get_session),
):
    """Clock a tech onto this activity. Creates an open TimeEntry."""
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    act = res.scalar_one_or_none()
    if not act:
        raise HTTPException(404, "Activity not found")

    tech = await session.get(Technician, payload.technician_id)
    if not tech:
        raise HTTPException(400, "Technician not found")

    # Don't double-clock the same tech
    open_entry = next(
        (te for te in act.time_entries if te.technician_id == payload.technician_id and te.ended_at is None),
        None,
    )
    if open_entry:
        raise HTTPException(409, f"{tech.name} is already clocked in on this activity")

    te = TimeEntry(
        activity_id=activity_id,
        technician_id=payload.technician_id,
        started_at=datetime.now(timezone.utc),
        note=payload.note,
    )
    session.add(te)

    if act.status in (ActivityStatus.PENDING, ActivityStatus.SCHEDULED, ActivityStatus.BLOCKED):
        act.status = ActivityStatus.IN_PROGRESS
        if not act.started_at:
            act.started_at = datetime.now(timezone.utc)
        if act.status == ActivityStatus.BLOCKED:
            act.blocker_reason = None

    session.add(
        ProjectEvent(
            project_id=act.project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"{tech.name} started: {act.title}",
        )
    )
    await session.commit()

    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    return await _to_out(session, res.scalar_one())


@router.post("/activities/{activity_id}/stop", response_model=ActivityOut)
async def stop_activity(
    activity_id: int,
    payload: ActivityStopIn,
    session: AsyncSession = Depends(get_session),
):
    """Close the open TimeEntry for the given tech on this activity."""
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    act = res.scalar_one_or_none()
    if not act:
        raise HTTPException(404, "Activity not found")

    tech = await session.get(Technician, payload.technician_id)
    if not tech:
        raise HTTPException(400, "Technician not found")

    open_entry = next(
        (te for te in act.time_entries if te.technician_id == payload.technician_id and te.ended_at is None),
        None,
    )
    if not open_entry:
        raise HTTPException(409, f"{tech.name} is not currently clocked in")

    now = datetime.now(timezone.utc)
    open_entry.ended_at = now
    elapsed = (now - open_entry.started_at).total_seconds() / 3600.0
    open_entry.hours = Decimal(str(round(elapsed, 2)))
    if payload.note:
        open_entry.note = (open_entry.note or "") + (f" / {payload.note}" if open_entry.note else payload.note)

    session.add(
        ProjectEvent(
            project_id=act.project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"{tech.name} stopped: {act.title} — logged {open_entry.hours}h",
        )
    )
    await session.commit()

    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    return await _to_out(session, res.scalar_one())


@router.post("/activities/{activity_id}/complete", response_model=ActivityOut)
async def complete_activity(activity_id: int, session: AsyncSession = Depends(get_session)):
    """Mark done. Closes any open time entries."""
    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    act = res.scalar_one_or_none()
    if not act:
        raise HTTPException(404, "Activity not found")

    now = datetime.now(timezone.utc)
    for te in act.time_entries:
        if te.ended_at is None:
            te.ended_at = now
            elapsed = (now - te.started_at).total_seconds() / 3600.0
            te.hours = Decimal(str(round(elapsed, 2)))

    act.status = ActivityStatus.DONE
    act.completed_at = now
    act.blocker_reason = None
    session.add(
        ProjectEvent(
            project_id=act.project_id,
            kind=ProjectEventKind.SCOPE_CHANGED,
            summary=f"Activity completed: {act.title}",
        )
    )
    await session.commit()

    res = await session.execute(
        select(Activity).options(selectinload(Activity.time_entries)).where(Activity.id == activity_id)
    )
    return await _to_out(session, res.scalar_one())


@router.get("/today", response_model=TodayBoard)
async def today_board(
    day: date_cls | None = Query(None, alias="date"),
    session: AsyncSession = Depends(get_session),
):
    target = day or date_cls.today()
    # Activities scheduled for that day OR in progress (not done, not skipped)
    res = await session.execute(
        select(Activity)
        .options(selectinload(Activity.time_entries), selectinload(Activity.project).selectinload(Project.client))
        .where(Activity.status != ActivityStatus.DONE)
        .where(Activity.status != ActivityStatus.SKIPPED)
        .where((Activity.scheduled_date == target) | (Activity.status == ActivityStatus.IN_PROGRESS))
    )
    activities = res.scalars().all()

    tech_res = await session.execute(select(Technician).where(Technician.active == True))  # noqa: E712
    techs = tech_res.scalars().all()

    by_tech: dict[int | None, list[Activity]] = {t.id: [] for t in techs}
    by_tech[None] = []  # unassigned bucket

    for a in activities:
        assigned = a.assigned_tech_ids or []
        if not assigned:
            by_tech[None].append(a)
        else:
            for tid in assigned:
                by_tech.setdefault(tid, []).append(a)

    columns: list[TodayTechColumn] = []
    for t in techs:
        acts = by_tech.get(t.id, [])
        scheduled_hours = sum((Decimal(a.estimated_hours or 0) for a in acts), Decimal("0"))
        today_activities = []
        for a in acts:
            out = await _to_out(session, a)
            today_activities.append(
                TodayActivity(
                    activity=out,
                    project_id=a.project_id,
                    project_title=a.project.title,
                    client_name=a.project.client.name,
                )
            )
        columns.append(
            TodayTechColumn(
                technician_id=t.id,
                technician_name=t.name,
                scheduled_hours=scheduled_hours,
                activities=today_activities,
                overload=scheduled_hours > Decimal("9"),
            )
        )

    if by_tech[None]:
        today_activities = []
        for a in by_tech[None]:
            out = await _to_out(session, a)
            today_activities.append(
                TodayActivity(
                    activity=out,
                    project_id=a.project_id,
                    project_title=a.project.title,
                    client_name=a.project.client.name,
                )
            )
        columns.append(
            TodayTechColumn(
                technician_id=None,
                technician_name="Unassigned",
                scheduled_hours=Decimal("0"),
                activities=today_activities,
                overload=False,
            )
        )

    return TodayBoard(date=target, columns=columns, total_activities=len(activities))
