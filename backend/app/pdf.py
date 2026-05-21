"""Quote PDF renderer. Jinja2 template → WeasyPrint PDF."""

from __future__ import annotations

import base64
import mimetypes
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from datetime import date as _date

from app.costing import compute_breakdown
from app.models import Invoice, InvoiceStatus, Project, Settings, Technician, VariationOrder, Vehicle

TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

# Logo baked into the backend image from the downloaded frontend asset
LOGO_PATH = Path(__file__).parent / "brand" / "logo.png"


def _logo_data_uri() -> str | None:
    if not LOGO_PATH.exists():
        return None
    mime, _ = mimetypes.guess_type(str(LOGO_PATH))
    mime = mime or "image/png"
    b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def render_quote_pdf(
    project: Project,
    settings: Settings,
    vehicle: Vehicle | None,
    technicians_by_id: dict[int, Technician],
) -> bytes:
    breakdown = compute_breakdown(project, vehicle, technicians_by_id)

    # Client-facing materials view — each BOM item with its line total
    materials: list[dict] = []
    materials_sum = Decimal("0")
    for m in project.materials or []:
        qty = Decimal(str(m.get("qty", 0) or 0))
        unit = Decimal(str(m.get("unit_cost", 0) or 0))
        line = qty * unit
        materials_sum += line
        materials.append(
            {
                "name": m.get("name", ""),
                "qty": qty,
                "unit_cost": unit,
                "line_total": line,
            }
        )

    # Bundle labour + travel + lodging + per-diem + contingency + margin into one line
    services_line = Decimal(str(breakdown["total_ex_vat"])) - materials_sum

    deposit_pct = Decimal(settings.deposit_pct_default or 0)
    total_inc_vat = Decimal(str(breakdown["total_inc_vat"]))
    deposit_amount = (total_inc_vat * deposit_pct / Decimal("100")).quantize(Decimal("0.01"))
    balance_amount = total_inc_vat - deposit_amount

    today = date.today()
    valid_until = today + timedelta(days=int(settings.quote_validity_days or 30))

    ctx = {
        "project": project,
        "settings": settings,
        "breakdown": breakdown,
        "materials": materials,
        "services_line": services_line,
        "quote_number": project.quote_number or f"BSP-Q-{project.id:04d}",
        "issue_date": today.strftime("%d %B %Y"),
        "valid_until": valid_until.strftime("%d %B %Y"),
        "deposit_pct": deposit_pct,
        "deposit_amount": deposit_amount,
        "balance_amount": balance_amount,
        "logo_data_uri": _logo_data_uri(),
    }

    template = _env.get_template("quote.html")
    html_str = template.render(**ctx)
    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf()
    return pdf_bytes


def render_invoice_pdf(invoice: Invoice, project: Project, settings: Settings) -> bytes:
    line_map = {
        "deposit": "Deposit on accepted quotation",
        "progress": "Progress invoice",
        "final": "Final invoice",
        "retention": "Release of retention",
    }
    line_title = line_map.get(invoice.type.value if hasattr(invoice.type, "value") else invoice.type, "Invoice")

    paid_total = sum((Decimal(p.amount) for p in invoice.payments), Decimal("0"))
    outstanding = Decimal(invoice.total_inc_vat) - paid_total
    today = _date.today()
    is_paid = invoice.status == InvoiceStatus.PAID
    is_overdue = (
        not is_paid
        and invoice.status != InvoiceStatus.CANCELLED
        and invoice.due_at < today
    )
    days_overdue = (today - invoice.due_at).days if is_overdue else 0

    ctx = {
        "invoice": invoice,
        "project": project,
        "settings": settings,
        "line_title": line_title,
        "payments": invoice.payments,
        "paid_total": paid_total,
        "outstanding": outstanding,
        "is_paid": is_paid,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "logo_data_uri": _logo_data_uri(),
    }
    template = _env.get_template("invoice.html")
    html_str = template.render(**ctx)
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf()


def render_variation_pdf(vo: VariationOrder, project: Project, settings: Settings) -> bytes:
    vat_amount = (Decimal(vo.cost_delta_ex_vat) * Decimal(vo.vat_pct_snapshot) / Decimal("100")).quantize(Decimal("0.01"))
    total_inc_vat = (Decimal(vo.cost_delta_ex_vat) + vat_amount).quantize(Decimal("0.01"))
    ctx = {
        "vo": vo,
        "project": project,
        "settings": settings,
        "issue_date": _date.today().strftime("%d %B %Y"),
        "vat_amount": vat_amount,
        "total_inc_vat": total_inc_vat,
        "logo_data_uri": _logo_data_uri(),
    }
    template = _env.get_template("variation.html")
    html_str = template.render(**ctx)
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf()
