"""CSV exports for accountants (Xero/Sage-friendly shape)."""

import csv
import io
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Expense, Invoice, InvoiceStatus, Project

router = APIRouter(prefix="/exports", tags=["exports"])


def _csv_response(rows: list[list], headers: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/invoices.csv")
async def export_invoices(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Xero-compatible Sales import. Minimum columns: ContactName, InvoiceNumber,
    InvoiceDate, DueDate, Description, Quantity, UnitAmount, AccountCode, TaxType."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.project).selectinload(Project.client))
        .where(Invoice.status != InvoiceStatus.CANCELLED)
        .order_by(Invoice.issued_at, Invoice.id)
    )
    if from_date is not None:
        stmt = stmt.where(Invoice.issued_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Invoice.issued_at <= to_date)
    res = await session.execute(stmt)
    rows: list[list] = []
    for inv in res.scalars().all():
        client_name = inv.project.client.name
        rows.append([
            client_name,
            inv.invoice_number,
            inv.issued_at.isoformat(),
            inv.due_at.isoformat(),
            (inv.description or f"{inv.type.value.title()} — {inv.project.title}"),
            "1",
            f"{inv.subtotal_ex_vat:.2f}",
            "200",  # Sales account code (tune to your chart in Xero)
            "Output VAT",  # Adjust per your Xero tax rate name
            inv.status.value,
        ])
    headers = [
        "ContactName",
        "InvoiceNumber",
        "InvoiceDate",
        "DueDate",
        "Description",
        "Quantity",
        "UnitAmount",
        "AccountCode",
        "TaxType",
        "Status",
    ]
    return _csv_response(rows, headers, "invoices-xero.csv")


@router.get("/expenses.csv")
async def export_expenses(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Expenses export. Columns suitable for Xero bank/cash transaction import."""
    stmt = (
        select(Expense)
        .options(selectinload(Expense.project).selectinload(Project.client))
        .order_by(Expense.incurred_at)
    )
    if from_date is not None:
        stmt = stmt.where(Expense.incurred_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Expense.incurred_at <= to_date)
    res = await session.execute(stmt)

    # Category → suggested Xero account code (tune these to your Xero chart)
    ACCOUNT_CODES = {
        "diesel": "449",  # Motor vehicle expenses
        "lodging": "455",  # Accommodation
        "meals": "456",  # Subsistence
        "tolls": "449",
        "materials": "310",  # COS - Direct materials
        "labour": "477",  # Sub-contractors
        "equipment_hire": "485",  # Equipment hire
        "other": "499",  # General expenses
    }
    rows: list[list] = []
    for e in res.scalars().all():
        p = e.project
        category = e.category.value if hasattr(e.category, "value") else e.category
        description = f"{category}: {e.description or ''} ({p.client.name} · {p.title})"
        rows.append([
            e.incurred_at.date().isoformat(),
            description.strip(" ·"),
            f"{Decimal(e.amount):.2f}",
            ACCOUNT_CODES.get(category, "499"),
            "Input VAT",
            f"P-{p.id}",  # Tracking category for per-project P&L in Xero
        ])
    headers = [
        "Date",
        "Description",
        "Amount",
        "AccountCode",
        "TaxType",
        "TrackingProject",
    ]
    return _csv_response(rows, headers, "expenses-xero.csv")
