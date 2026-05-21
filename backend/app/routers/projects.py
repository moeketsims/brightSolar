from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.costing import compute_breakdown
from app.db import get_session
from app.models import (
    Activity,
    ActivityStatus,
    Client,
    Expense,
    Invoice,
    InvoiceStatus,
    Project,
    ProjectEvent,
    ProjectEventKind,
    ProjectStatus,
    Technician,
    Vehicle,
)
from app.pdf import render_quote_pdf
from app.reconciliation import build_reconciliation
from app.routers.activities import _to_out as activity_to_out
from app.routers.settings import get_or_create_settings
from app.schemas import (
    AcceptQuoteIn,
    ActivityOut,
    ActualTotals,
    AgedDebtors,
    ApplySuggestionIn,
    CostBreakdown,
    DashboardOut,
    DashboardProjectCard,
    ProjectDetail,
    ProjectEventOut,
    ProjectInputs,
    ProjectNoteIn,
    ProjectSummary,
    ProjectUpdate,
    ReconciliationOut,
)

router = APIRouter(prefix="/projects", tags=["projects"])

CLOSED_STATUSES = {ProjectStatus.COMPLETED, ProjectStatus.INVOICED, ProjectStatus.PAID, ProjectStatus.LOST}


async def _load_tech_map(session: AsyncSession) -> dict[int, Technician]:
    res = await session.execute(select(Technician))
    return {t.id: t for t in res.scalars().all()}


def _actual_totals(project: Project) -> ActualTotals:
    by_cat: dict[str, Decimal] = {}
    total = Decimal("0")
    for e in project.expenses:
        amt = Decimal(e.amount)
        total += amt
        by_cat[e.category.value] = by_cat.get(e.category.value, Decimal("0")) + amt
    return ActualTotals(total=total, by_category=by_cat)


async def _load_events(session: AsyncSession, project_id: int) -> list[ProjectEvent]:
    res = await session.execute(
        select(ProjectEvent)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.created_at.desc())
    )
    return res.scalars().all()


async def _to_detail(project: Project, session: AsyncSession) -> ProjectDetail:
    tech_map = await _load_tech_map(session)
    breakdown = compute_breakdown(project, project.vehicle, tech_map)
    actuals = _actual_totals(project)
    events = await _load_events(session, project.id)
    activities: list[ActivityOut] = []
    for a in project.activities:
        activities.append(await activity_to_out(session, a))
    return ProjectDetail(
        id=project.id,
        client=project.client,
        title=project.title,
        service_type=project.service_type,
        status=project.status,
        site_address=project.site_address,
        description=project.description,
        quote_number=project.quote_number,
        accepted_at=project.accepted_at,
        accepted_by_name=project.accepted_by_name,
        one_way_distance_km=project.one_way_distance_km,
        return_trips=project.return_trips,
        vehicle=project.vehicle,
        estimated_hours_on_site=project.estimated_hours_on_site,
        estimated_travel_hours=project.estimated_travel_hours,
        overnight_nights=project.overnight_nights,
        people_on_site=project.people_on_site,
        contingency_pct=project.contingency_pct,
        margin_pct=project.margin_pct,
        vat_pct=project.vat_pct,
        diesel_price_snapshot=project.diesel_price_snapshot,
        lodging_rate_snapshot=project.lodging_rate_snapshot,
        per_diem_snapshot=project.per_diem_snapshot,
        materials=project.materials or [],
        tech_assignments=project.tech_assignments or [],
        activities=activities,
        quoted=CostBreakdown(**breakdown),
        actuals=actuals,
        expenses=project.expenses,
        events=[ProjectEventOut.model_validate(e) for e in events],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _diff_summary(
    old: Project,
    new_data: dict,
    tech_map: dict[int, Technician],
) -> tuple[str, list[str], ProjectEventKind]:
    """Produce a short summary + detail bullets describing what changed."""
    bullets: list[str] = []
    kind = ProjectEventKind.UPDATED

    def push(b: str) -> None:
        bullets.append(b)

    def num(v) -> Decimal:
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal("0")

    simple_fields = [
        ("title", "Title"),
        ("description", "Description"),
        ("site_address", "Site address"),
        ("one_way_distance_km", "Distance (one-way km)"),
        ("return_trips", "Return trips"),
        ("estimated_hours_on_site", "Hours on site"),
        ("estimated_travel_hours", "Travel hours"),
        ("overnight_nights", "Overnight nights"),
        ("people_on_site", "People on site"),
        ("contingency_pct", "Contingency %"),
        ("margin_pct", "Margin %"),
    ]
    for key, label in simple_fields:
        if key in new_data:
            before = getattr(old, key)
            after = new_data[key]
            if str(before) != str(after):
                push(f"{label}: {before} → {after}")

    if "status" in new_data and new_data["status"] is not None and str(new_data["status"]) != str(old.status.value if hasattr(old.status, "value") else old.status):
        kind = ProjectEventKind.STATUS_CHANGED
        old_status = old.status.value if hasattr(old.status, "value") else old.status
        new_status = new_data["status"].value if hasattr(new_data["status"], "value") else new_data["status"]
        push(f"Status: {old_status} → {new_status}")

    if "vehicle_id" in new_data and new_data["vehicle_id"] != old.vehicle_id:
        push(f"Vehicle changed")

    if "tech_assignments" in new_data and new_data["tech_assignments"] is not None:
        before_ids = {a.get("technician_id"): a for a in (old.tech_assignments or [])}
        after_ids = {a.get("technician_id"): a for a in new_data["tech_assignments"]}
        added = set(after_ids) - set(before_ids)
        removed = set(before_ids) - set(after_ids)
        for tid in added:
            name = tech_map.get(tid, None)
            h = after_ids[tid].get("hours", 0)
            d = after_ids[tid].get("days", 0)
            push(f"+ Tech added: {name.name if name else f'#{tid}'} ({h}h, {d}d)")
        for tid in removed:
            name = tech_map.get(tid, None)
            push(f"− Tech removed: {name.name if name else f'#{tid}'}")
        # Detect hours/days change for kept techs
        for tid in set(after_ids) & set(before_ids):
            b = before_ids[tid]
            a = after_ids[tid]
            if num(b.get("hours", 0)) != num(a.get("hours", 0)) or num(b.get("days", 0)) != num(a.get("days", 0)):
                name = tech_map.get(tid, None)
                push(f"  {name.name if name else f'#{tid}'}: {b.get('hours', 0)}h/{b.get('days', 0)}d → {a.get('hours', 0)}h/{a.get('days', 0)}d")
        if added or removed:
            kind = ProjectEventKind.TECH_ADDED if added else ProjectEventKind.TECH_REMOVED

    if "materials" in new_data and new_data["materials"] is not None:
        b_total = sum(num(m.get("qty", 0)) * num(m.get("unit_cost", 0)) for m in (old.materials or []))
        a_total = sum(num(m.get("qty", 0)) * num(m.get("unit_cost", 0)) for m in new_data["materials"])
        if b_total != a_total or len(old.materials or []) != len(new_data["materials"]):
            push(f"Materials updated: {len(old.materials or [])} → {len(new_data['materials'])} items (R{b_total} → R{a_total})")

    if not bullets:
        return "", [], kind
    summary = "; ".join(bullets[:2])
    if len(bullets) > 2:
        summary += f" (+{len(bullets) - 2} more)"
    return summary, bullets, kind


@router.post("/preview", response_model=CostBreakdown)
async def preview_breakdown(payload: ProjectInputs, session: AsyncSession = Depends(get_session)):
    s = await get_or_create_settings(session)
    vehicle = await session.get(Vehicle, payload.vehicle_id) if payload.vehicle_id else None
    tech_map = await _load_tech_map(session)

    tmp = Project(
        client_id=payload.client_id,
        title=payload.title,
        service_type=payload.service_type,
        site_address=payload.site_address,
        description=payload.description,
        one_way_distance_km=payload.one_way_distance_km,
        return_trips=payload.return_trips,
        vehicle_id=payload.vehicle_id,
        estimated_hours_on_site=payload.estimated_hours_on_site,
        estimated_travel_hours=payload.estimated_travel_hours,
        overnight_nights=payload.overnight_nights,
        people_on_site=payload.people_on_site,
        diesel_price_snapshot=s.diesel_price_per_litre,
        lodging_rate_snapshot=s.default_lodging_per_night,
        per_diem_snapshot=s.default_per_diem,
        contingency_pct=payload.contingency_pct if payload.contingency_pct is not None else s.default_contingency_pct,
        margin_pct=payload.margin_pct if payload.margin_pct is not None else s.default_margin_pct,
        vat_pct=s.vat_pct,
        materials=[m.model_dump(mode="json") for m in payload.materials],
        tech_assignments=[a.model_dump(mode="json") for a in payload.tech_assignments],
    )
    breakdown = compute_breakdown(tmp, vehicle, tech_map)
    return CostBreakdown(**breakdown)


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(payload: ProjectInputs, session: AsyncSession = Depends(get_session)):
    client = await session.get(Client, payload.client_id)
    if not client:
        raise HTTPException(400, "Client not found")

    s = await get_or_create_settings(session)
    template_name: str | None = None
    if payload.from_template_id is not None:
        from app.models import ServiceTemplate
        tpl = await session.get(ServiceTemplate, payload.from_template_id)
        if tpl:
            template_name = tpl.name

    project = Project(
        client_id=payload.client_id,
        title=payload.title,
        service_type=payload.service_type,
        site_address=payload.site_address,
        description=payload.description,
        one_way_distance_km=payload.one_way_distance_km,
        return_trips=payload.return_trips,
        vehicle_id=payload.vehicle_id,
        estimated_hours_on_site=payload.estimated_hours_on_site,
        estimated_travel_hours=payload.estimated_travel_hours,
        overnight_nights=payload.overnight_nights,
        people_on_site=payload.people_on_site,
        diesel_price_snapshot=s.diesel_price_per_litre,
        lodging_rate_snapshot=s.default_lodging_per_night,
        per_diem_snapshot=s.default_per_diem,
        contingency_pct=payload.contingency_pct if payload.contingency_pct is not None else s.default_contingency_pct,
        margin_pct=payload.margin_pct if payload.margin_pct is not None else s.default_margin_pct,
        vat_pct=s.vat_pct,
        materials=[m.model_dump(mode="json") for m in payload.materials],
        tech_assignments=[a.model_dump(mode="json") for a in payload.tech_assignments],
    )
    session.add(project)
    await session.flush()

    # Instantiate initial activities (from template or user-provided)
    for i, a in enumerate(payload.initial_activities or []):
        session.add(
            Activity(
                project_id=project.id,
                title=a.title,
                description=a.description,
                estimated_hours=a.estimated_hours,
                position=a.position if a.position is not None else i,
                status=ActivityStatus.PENDING,
            )
        )

    vehicle = await session.get(Vehicle, project.vehicle_id) if project.vehicle_id else None
    tech_map = await _load_tech_map(session)
    bd = compute_breakdown(project, vehicle, tech_map)
    project.quoted_total_ex_vat = Decimal(str(bd["total_ex_vat"]))
    project.quoted_total_inc_vat = Decimal(str(bd["total_inc_vat"]))

    created_summary = f"Project created — quoted at R{project.quoted_total_inc_vat:,.2f} inc VAT"
    if template_name:
        created_summary += f" (from template: {template_name})"
    session.add(
        ProjectEvent(
            project_id=project.id,
            kind=ProjectEventKind.CREATED,
            summary=created_summary,
            quote_after=project.quoted_total_inc_vat,
        )
    )

    await session.commit()

    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
            selectinload(Project.expenses),
            selectinload(Project.activities).selectinload(Activity.time_entries),
        )
        .where(Project.id == project.id)
    )
    return await _to_detail(res.scalar_one(), session)


@router.get("", response_model=list[ProjectSummary])
async def list_projects(session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Project).options(selectinload(Project.client), selectinload(Project.expenses))
        .order_by(Project.created_at.desc())
    )
    out: list[ProjectSummary] = []
    for p in res.scalars().all():
        actual = sum((Decimal(e.amount) for e in p.expenses), Decimal("0"))
        quoted_ex_vat = Decimal(p.quoted_total_ex_vat or 0)
        margin_ex = quoted_ex_vat - actual
        margin_pct = float((margin_ex / quoted_ex_vat * 100) if quoted_ex_vat > 0 else Decimal("0"))
        out.append(
            ProjectSummary(
                id=p.id,
                client_id=p.client_id,
                client_name=p.client.name,
                title=p.title,
                service_type=p.service_type,
                status=p.status,
                site_address=p.site_address,
                quoted_total_ex_vat=quoted_ex_vat,
                quoted_total_inc_vat=p.quoted_total_inc_vat or Decimal("0"),
                actual_total=actual,
                margin_ex_vat=margin_ex,
                margin_pct_realised=margin_pct,
                created_at=p.created_at,
            )
        )
    return out


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
            selectinload(Project.expenses),
            selectinload(Project.activities).selectinload(Activity.time_entries),
        )
        .where(Project.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return await _to_detail(project, session)


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(project_id: int, payload: ProjectUpdate, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Block edits on closed projects unless only changing status
    data = payload.model_dump(exclude_unset=True, mode="json")
    non_status_keys = [k for k in data if k != "status"]
    if project.status in CLOSED_STATUSES and non_status_keys:
        raise HTTPException(
            409,
            f"Project is {project.status.value}. Reopen it (change status) before editing other fields.",
        )

    quote_before = Decimal(project.quoted_total_inc_vat or 0)
    tech_map = await _load_tech_map(session)
    summary, bullets, kind = _diff_summary(project, data, tech_map)

    if "materials" in data and data["materials"] is not None:
        data["materials"] = [m.model_dump(mode="json") if hasattr(m, "model_dump") else m for m in data["materials"]]
    if "tech_assignments" in data and data["tech_assignments"] is not None:
        data["tech_assignments"] = [a.model_dump(mode="json") if hasattr(a, "model_dump") else a for a in data["tech_assignments"]]
    for k, v in data.items():
        setattr(project, k, v)

    vehicle = await session.get(Vehicle, project.vehicle_id) if project.vehicle_id else None
    bd = compute_breakdown(project, vehicle, tech_map)
    project.quoted_total_ex_vat = Decimal(str(bd["total_ex_vat"]))
    project.quoted_total_inc_vat = Decimal(str(bd["total_inc_vat"]))

    if summary:
        delta = Decimal(project.quoted_total_inc_vat) - quote_before
        if delta != 0:
            summary = f"{summary} — quote {quote_before:,.0f} → {project.quoted_total_inc_vat:,.0f} ({'+' if delta > 0 else ''}R{delta:,.0f})"
        session.add(
            ProjectEvent(
                project_id=project.id,
                kind=kind,
                summary=summary,
                details="\n".join(bullets) if bullets else None,
                quote_before=quote_before,
                quote_after=project.quoted_total_inc_vat,
            )
        )

    await session.commit()

    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
            selectinload(Project.expenses),
            selectinload(Project.activities).selectinload(Activity.time_entries),
        )
        .where(Project.id == project_id)
    )
    return await _to_detail(res.scalar_one(), session)


@router.post("/{project_id}/accept", response_model=ProjectDetail)
async def accept_quote(
    project_id: int,
    payload: AcceptQuoteIn,
    session: AsyncSession = Depends(get_session),
):
    """Client accepted the quote — stamp it and transition status."""
    from datetime import datetime, timezone as tz
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if project.accepted_at:
        raise HTTPException(409, f"Quote already accepted by {project.accepted_by_name} on {project.accepted_at.date()}.")

    now = datetime.now(tz.utc)
    project.accepted_at = now
    project.accepted_by_name = payload.accepted_by_name.strip()
    if project.status in (ProjectStatus.QUOTING, ProjectStatus.QUOTED):
        project.status = ProjectStatus.ACCEPTED
    session.add(
        ProjectEvent(
            project_id=project_id,
            kind=ProjectEventKind.STATUS_CHANGED,
            summary=f"Quote accepted by {project.accepted_by_name} — status set to accepted",
            quote_before=project.quoted_total_inc_vat,
            quote_after=project.quoted_total_inc_vat,
        )
    )
    await session.commit()

    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
            selectinload(Project.expenses),
            selectinload(Project.activities).selectinload(Activity.time_entries),
        )
        .where(Project.id == project_id)
    )
    return await _to_detail(res.scalar_one(), session)


@router.post("/{project_id}/notes", response_model=ProjectEventOut, status_code=201)
async def add_note(project_id: int, payload: ProjectNoteIn, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    ev = ProjectEvent(
        project_id=project_id,
        kind=ProjectEventKind.NOTE,
        summary=payload.note[:120] + ("…" if len(payload.note) > 120 else ""),
        note=payload.note,
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev


@router.get("/{project_id}/reconciliation", response_model=ReconciliationOut)
async def project_reconciliation(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
            selectinload(Project.expenses),
            selectinload(Project.activities).selectinload(Activity.time_entries),
        )
        .where(Project.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    tech_map = await _load_tech_map(session)
    settings = await get_or_create_settings(session)
    return build_reconciliation(project, project.vehicle, tech_map, settings)


@router.post("/{project_id}/reconciliation/apply")
async def apply_reconciliation_suggestion(
    project_id: int,
    payload: ApplySuggestionIn,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if payload.target == "settings":
        settings = await get_or_create_settings(session)
        if not hasattr(settings, payload.field):
            raise HTTPException(400, f"Unknown settings field: {payload.field}")
        old = getattr(settings, payload.field)
        setattr(settings, payload.field, payload.value)
        session.add(
            ProjectEvent(
                project_id=project_id,
                kind=ProjectEventKind.NOTE,
                summary=f"Learned from reconciliation: {payload.field} {old} → {payload.value}",
                note=f"Applied suggestion {payload.suggestion_id} — future quotes use the new default.",
            )
        )
    elif payload.target.startswith("vehicle:"):
        vehicle_id = int(payload.target.split(":", 1)[1])
        vehicle = await session.get(Vehicle, vehicle_id)
        if not vehicle:
            raise HTTPException(400, "Vehicle not found")
        if not hasattr(vehicle, payload.field):
            raise HTTPException(400, f"Unknown vehicle field: {payload.field}")
        old = getattr(vehicle, payload.field)
        setattr(vehicle, payload.field, payload.value)
        session.add(
            ProjectEvent(
                project_id=project_id,
                kind=ProjectEventKind.NOTE,
                summary=f"Learned from reconciliation: {vehicle.name} {payload.field} {old} → {payload.value}",
                note=f"Applied suggestion {payload.suggestion_id} — future quotes use the new vehicle rate.",
            )
        )
    else:
        raise HTTPException(400, f"Unknown target: {payload.target}")

    await session.commit()
    return {"applied": True, "field": payload.field, "target": payload.target, "value": str(payload.value)}


@router.get("/{project_id}/quote.pdf")
async def project_quote_pdf(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.vehicle),
        )
        .where(Project.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Assign a quote number on first render and persist it
    if not project.quote_number:
        project.quote_number = f"BSP-Q-{project.id:04d}"
        await session.commit()

    settings_row = await get_or_create_settings(session)
    tech_map = await _load_tech_map(session)

    pdf_bytes = render_quote_pdf(project, settings_row, project.vehicle, tech_map)

    safe_client = "".join(c for c in project.client.name if c.isalnum() or c in (" ", "-")).strip()[:40] or "client"
    filename = f"{project.quote_number}-{safe_client.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await session.delete(project)
    await session.commit()


@router.get("/dashboard/summary", response_model=DashboardOut)
async def dashboard(session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Project).options(selectinload(Project.client), selectinload(Project.expenses))
        .order_by(Project.created_at.desc())
    )
    projects = res.scalars().all()

    month_start = date.today().replace(day=1)
    cards: list[DashboardProjectCard] = []
    active_count = 0
    over_count = 0
    pipeline = Decimal("0")
    month_expenses = Decimal("0")

    for p in projects:
        actual = sum((Decimal(e.amount) for e in p.expenses), Decimal("0"))
        month_expenses += sum(
            (Decimal(e.amount) for e in p.expenses if e.incurred_at.date() >= month_start),
            Decimal("0"),
        )
        quoted_ex_vat = Decimal(p.quoted_total_ex_vat or 0)
        is_active = p.status.value in ("quoted", "accepted", "in_progress")
        if is_active:
            active_count += 1
            pipeline += Decimal(p.quoted_total_inc_vat or 0)

        burn = float((actual / quoted_ex_vat) if quoted_ex_vat > 0 else Decimal("0"))
        colour = "green" if burn < 0.7 else ("amber" if burn < 1.0 else "red")
        if burn >= 1.0:
            over_count += 1

        cards.append(
            DashboardProjectCard(
                id=p.id,
                client_name=p.client.name,
                title=p.title,
                status=p.status,
                quoted_inc_vat=p.quoted_total_inc_vat or Decimal("0"),
                quoted_ex_vat=quoted_ex_vat,
                actual_total=actual,
                burn_ratio=burn,
                status_colour=colour,
            )
        )

    cards.sort(key=lambda c: (c.status_colour == "red", c.status_colour == "amber", c.burn_ratio), reverse=True)

    # Activity KPIs
    act_res = await session.execute(select(Activity))
    acts = act_res.scalars().all()
    today = date.today()
    in_progress = sum(1 for a in acts if a.status == ActivityStatus.IN_PROGRESS)
    blocked = sum(1 for a in acts if a.status == ActivityStatus.BLOCKED)
    overdue = sum(
        1
        for a in acts
        if a.status not in (ActivityStatus.DONE, ActivityStatus.SKIPPED)
        and a.due_date is not None
        and a.due_date < today
    )

    # Aged debtors — all unpaid invoices, bucketed by days overdue
    inv_res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments))
    )
    invoices = inv_res.scalars().all()
    bucket = {"0_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "90_plus": Decimal("0")}
    overdue_count = 0
    for inv in invoices:
        if inv.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            continue
        paid = sum((Decimal(p.amount) for p in inv.payments), Decimal("0"))
        outstanding = Decimal(inv.total_inc_vat) - paid
        if outstanding <= 0:
            continue
        days = (today - inv.due_at).days
        if days > 0:
            overdue_count += 1
        if days <= 30:
            bucket["0_30"] += outstanding
        elif days <= 60:
            bucket["31_60"] += outstanding
        elif days <= 90:
            bucket["61_90"] += outstanding
        else:
            bucket["90_plus"] += outstanding
    total_out = sum(bucket.values(), Decimal("0"))
    debtors = AgedDebtors(
        bucket_0_30=bucket["0_30"],
        bucket_31_60=bucket["31_60"],
        bucket_61_90=bucket["61_90"],
        bucket_90_plus=bucket["90_plus"],
        total_outstanding=total_out,
        overdue_count=overdue_count,
    )

    return DashboardOut(
        active_projects=active_count,
        quoted_pipeline=pipeline,
        expenses_this_month=month_expenses,
        projects_over_budget=over_count,
        activities_in_progress=in_progress,
        activities_overdue=overdue,
        activities_blocked=blocked,
        debtors=debtors,
        cards=cards,
    )
