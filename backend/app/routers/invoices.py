from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Payment,
    Project,
    ProjectEvent,
    ProjectEventKind,
)
from app.routers.settings import get_or_create_settings
from app.schemas import (
    InvoiceCreate,
    InvoiceOut,
    InvoiceUpdate,
    InvoiceWithProject,
    PaymentCreate,
    PaymentOut,
)

router = APIRouter(tags=["invoices"])


def _round(v: Decimal) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"))


def _next_invoice_number(existing: list[str]) -> str:
    year = date.today().year
    max_seq = 0
    prefix = f"BSP-INV-{year}-"
    for n in existing:
        if n and n.startswith(prefix):
            try:
                seq = int(n.split("-")[-1])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass
    return f"{prefix}{max_seq + 1:04d}"


def _paid_total(inv: Invoice) -> Decimal:
    return sum((Decimal(p.amount) for p in inv.payments), Decimal("0"))


def _apply_payment_status(inv: Invoice) -> None:
    """If payments sum >= total, transition to PAID."""
    paid = _paid_total(inv)
    if paid >= Decimal(inv.total_inc_vat) and inv.status != InvoiceStatus.CANCELLED:
        inv.status = InvoiceStatus.PAID


def _to_out(inv: Invoice) -> InvoiceOut:
    paid = _paid_total(inv)
    outstanding = Decimal(inv.total_inc_vat) - paid
    today = date.today()
    overdue = (
        inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED)
        and inv.due_at < today
    )
    days_overdue = (today - inv.due_at).days if overdue else 0
    return InvoiceOut(
        id=inv.id,
        project_id=inv.project_id,
        invoice_number=inv.invoice_number,
        type=inv.type,
        status=inv.status,
        issued_at=inv.issued_at,
        due_at=inv.due_at,
        subtotal_ex_vat=inv.subtotal_ex_vat,
        vat=inv.vat,
        total_inc_vat=inv.total_inc_vat,
        retention_pct=inv.retention_pct,
        retention_amount=inv.retention_amount,
        description=inv.description,
        notes=inv.notes,
        sent_at=inv.sent_at,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        paid_total=_round(paid),
        outstanding=_round(outstanding),
        is_overdue=overdue,
        days_overdue=days_overdue,
        payments=[PaymentOut.model_validate(p) for p in inv.payments],
    )


async def _suggest_amount(
    session: AsyncSession, project: Project, inv_type: InvoiceType
) -> Decimal:
    """Suggest an invoice amount based on type + existing invoices."""
    settings = await get_or_create_settings(session)
    total = Decimal(project.quoted_total_inc_vat or 0)
    # Sum existing invoice totals (ex cancelled)
    existing_total = sum(
        (Decimal(i.total_inc_vat) for i in project.invoices if i.status != InvoiceStatus.CANCELLED),
        Decimal("0"),
    )
    if inv_type == InvoiceType.DEPOSIT:
        pct = Decimal(settings.deposit_pct_default or 0)
        return _round(total * pct / Decimal("100"))
    if inv_type == InvoiceType.FINAL:
        return _round(max(Decimal("0"), total - existing_total))
    if inv_type == InvoiceType.PROGRESS:
        # half of the remaining
        remaining = max(Decimal("0"), total - existing_total)
        return _round(remaining / Decimal("2"))
    if inv_type == InvoiceType.RETENTION:
        return Decimal("0")  # user-entered
    return Decimal("0")


@router.get("/projects/{project_id}/invoices", response_model=list[InvoiceOut])
async def list_project_invoices(project_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Invoice)
        .options(selectinload(Invoice.payments))
        .where(Invoice.project_id == project_id)
        .order_by(Invoice.issued_at, Invoice.id)
    )
    return [_to_out(i) for i in res.scalars().all()]


@router.post("/projects/{project_id}/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    project_id: int,
    payload: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(Project)
        .options(selectinload(Project.invoices))
        .where(Project.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    if Decimal(project.quoted_total_inc_vat or 0) <= 0:
        raise HTTPException(400, "Project has no quoted total — save the quote first")

    # Determine amount
    if payload.subtotal_ex_vat is not None:
        subtotal = _round(Decimal(payload.subtotal_ex_vat))
    else:
        total_suggested = await _suggest_amount(session, project, payload.type)
        # Suggest subtotal ex VAT = total / (1 + VAT%)
        vat_pct = Decimal(project.vat_pct or 0)
        subtotal = _round(total_suggested / (Decimal("1") + vat_pct / Decimal("100")))

    vat_pct = Decimal(project.vat_pct or 0)
    vat = _round(subtotal * vat_pct / Decimal("100"))
    total = _round(subtotal + vat)

    # Retention applies to progress / final — holds back a portion
    retention_pct = Decimal(payload.retention_pct or 0)
    retention_amount = _round(total * retention_pct / Decimal("100")) if retention_pct > 0 else Decimal("0")

    # Due date — default: 30 days out
    due = payload.due_at or (date.today() + timedelta(days=30))

    # Number
    nums_res = await session.execute(select(Invoice.invoice_number))
    existing_numbers = [n for (n,) in nums_res.all()]
    number = _next_invoice_number(existing_numbers)

    inv = Invoice(
        project_id=project_id,
        invoice_number=number,
        type=payload.type,
        status=InvoiceStatus.DRAFT,
        issued_at=date.today(),
        due_at=due,
        subtotal_ex_vat=subtotal,
        vat=vat,
        total_inc_vat=total,
        retention_pct=retention_pct,
        retention_amount=retention_amount,
        description=payload.description,
        notes=payload.notes,
    )
    session.add(inv)
    session.add(
        ProjectEvent(
            project_id=project_id,
            kind=ProjectEventKind.NOTE,
            summary=f"Invoice {number} ({payload.type.value}) drafted — R{total:,.2f} inc VAT",
        )
    )
    await session.commit()

    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == inv.id)
    )
    return _to_out(res.scalar_one())


@router.get("/invoices", response_model=list[InvoiceWithProject])
async def list_all_invoices(
    status: InvoiceStatus | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.payments),
            selectinload(Invoice.project).selectinload(Project.client),
        )
        .order_by(Invoice.issued_at.desc(), Invoice.id.desc())
    )
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    res = await session.execute(stmt)
    out: list[InvoiceWithProject] = []
    for inv in res.scalars().all():
        base = _to_out(inv).model_dump()
        out.append(
            InvoiceWithProject(
                **base,
                project_title=inv.project.title,
                client_name=inv.project.client.name,
            )
        )
    return out


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _to_out(inv)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    data = payload.model_dump(exclude_unset=True, mode="json")
    if "status" in data:
        new_status = data["status"]
        if new_status == "sent" and inv.sent_at is None:
            inv.sent_at = datetime.now(timezone.utc)
        if new_status != "paid" or _paid_total(inv) >= Decimal(inv.total_inc_vat):
            pass
        elif new_status == "paid":
            # Only allow paid if actually paid
            raise HTTPException(400, "Cannot mark paid — payments recorded are less than the total")
        inv.status = new_status  # type: ignore[assignment]
        session.add(
            ProjectEvent(
                project_id=inv.project_id,
                kind=ProjectEventKind.NOTE,
                summary=f"Invoice {inv.invoice_number}: status → {new_status}",
            )
        )
    for k, v in data.items():
        if k != "status":
            setattr(inv, k, v)

    await session.commit()
    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
    )
    return _to_out(res.scalar_one())


@router.delete("/invoices/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: int, session: AsyncSession = Depends(get_session)):
    inv = await session.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status not in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED):
        raise HTTPException(409, "Cannot delete a sent / paid invoice. Cancel it instead.")
    await session.delete(inv)
    await session.commit()


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentOut, status_code=201)
async def record_payment(
    invoice_id: int,
    payload: PaymentCreate,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == InvoiceStatus.CANCELLED:
        raise HTTPException(409, "Cannot record payment on cancelled invoice")
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be positive")

    p = Payment(
        invoice_id=invoice_id,
        received_at=payload.received_at or date.today(),
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        note=payload.note,
    )
    session.add(p)
    await session.flush()
    # Reload to include new payment
    await session.refresh(inv, attribute_names=["payments"])
    _apply_payment_status(inv)
    session.add(
        ProjectEvent(
            project_id=inv.project_id,
            kind=ProjectEventKind.NOTE,
            summary=f"Payment R{payload.amount:,.2f} received on {inv.invoice_number} ({payload.method}){' — invoice PAID' if inv.status == InvoiceStatus.PAID else ''}",
        )
    )
    await session.commit()
    await session.refresh(p)
    return PaymentOut.model_validate(p)


@router.delete("/invoices/{invoice_id}/payments/{payment_id}", status_code=204)
async def delete_payment(
    invoice_id: int,
    payment_id: int,
    session: AsyncSession = Depends(get_session),
):
    p = await session.get(Payment, payment_id)
    if not p or p.invoice_id != invoice_id:
        raise HTTPException(404, "Payment not found")
    await session.delete(p)
    # Re-apply status
    res = await session.execute(
        select(Invoice).options(selectinload(Invoice.payments)).where(Invoice.id == invoice_id)
    )
    inv = res.scalar_one()
    if inv.status == InvoiceStatus.PAID and _paid_total(inv) < Decimal(inv.total_inc_vat):
        inv.status = InvoiceStatus.SENT if inv.sent_at else InvoiceStatus.DRAFT
    await session.commit()


@router.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: int, session: AsyncSession = Depends(get_session)):
    from app.pdf import render_invoice_pdf

    res = await session.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.payments),
            selectinload(Invoice.project).selectinload(Project.client),
        )
        .where(Invoice.id == invoice_id)
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    settings_row = await get_or_create_settings(session)
    pdf_bytes = render_invoice_pdf(inv, inv.project, settings_row)

    safe = "".join(c for c in inv.project.client.name if c.isalnum() or c in (" ", "-")).strip()[:30] or "client"
    filename = f"{inv.invoice_number}-{safe.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
