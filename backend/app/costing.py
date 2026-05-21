"""Costing engine — transparent breakdown so owners can audit every number."""

from decimal import Decimal
from typing import TypedDict

from app.models import Project, Technician, Vehicle


class CostLine(TypedDict):
    key: str
    label: str
    detail: str
    amount: float


class CostBreakdown(TypedDict):
    lines: list[CostLine]
    subtotal: float
    contingency: float
    margin: float
    total_ex_vat: float
    vat: float
    total_inc_vat: float


def _round(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"))


def compute_breakdown(
    project: Project,
    vehicle: Vehicle | None,
    technicians_by_id: dict[int, Technician],
) -> CostBreakdown:
    lines: list[CostLine] = []

    # Travel / diesel
    distance = Decimal(project.one_way_distance_km) * Decimal(project.return_trips) * 2
    if vehicle and distance > 0:
        litres = distance * Decimal(vehicle.fuel_consumption_l_per_100km) / Decimal("100")
        diesel_cost = _round(litres * Decimal(project.diesel_price_snapshot))
        lines.append(
            {
                "key": "diesel",
                "label": "Diesel",
                "detail": f"{distance} km @ {vehicle.fuel_consumption_l_per_100km} L/100km × R{project.diesel_price_snapshot}/L = {litres:.1f} L",
                "amount": float(diesel_cost),
            }
        )
        vehicle_wear = _round(distance * Decimal(vehicle.running_cost_per_km))
        lines.append(
            {
                "key": "vehicle_wear",
                "label": "Vehicle running cost",
                "detail": f"{distance} km × R{vehicle.running_cost_per_km}/km",
                "amount": float(vehicle_wear),
            }
        )
    elif distance > 0:
        lines.append(
            {
                "key": "diesel",
                "label": "Diesel",
                "detail": "No vehicle selected — pick one to compute fuel",
                "amount": 0.0,
            }
        )

    # Labour — additive: either hours at hourly rate, days at daily rate, or both
    labour_total = Decimal("0")
    labour_details: list[str] = []
    for a in project.tech_assignments or []:
        tech = technicians_by_id.get(a.get("technician_id"))
        if not tech:
            continue
        hours = Decimal(str(a.get("hours", 0) or 0))
        days = Decimal(str(a.get("days", 0) or 0))
        parts: list[str] = []
        cost = Decimal("0")
        if hours > 0:
            cost += _round(hours * Decimal(tech.hourly_rate))
            parts.append(f"{hours}h × R{tech.hourly_rate}")
        if days > 0:
            cost += _round(days * Decimal(tech.daily_rate))
            parts.append(f"{days}d × R{tech.daily_rate}")
        if cost > 0:
            labour_details.append(f"{tech.name}: {' + '.join(parts)}")
            labour_total += cost
    if labour_total > 0:
        lines.append(
            {
                "key": "labour",
                "label": "Labour",
                "detail": " · ".join(labour_details) or "—",
                "amount": float(labour_total),
            }
        )

    # Lodging + per diem
    if project.overnight_nights > 0 and project.people_on_site > 0:
        lodging = _round(Decimal(project.overnight_nights) * Decimal(project.lodging_rate_snapshot) * Decimal(project.people_on_site))
        lines.append(
            {
                "key": "lodging",
                "label": "Lodging",
                "detail": f"{project.overnight_nights} night(s) × R{project.lodging_rate_snapshot} × {project.people_on_site} people",
                "amount": float(lodging),
            }
        )
        per_diem = _round(Decimal(project.overnight_nights) * Decimal(project.per_diem_snapshot) * Decimal(project.people_on_site))
        lines.append(
            {
                "key": "per_diem",
                "label": "Per diem (meals)",
                "detail": f"{project.overnight_nights} × R{project.per_diem_snapshot} × {project.people_on_site} people",
                "amount": float(per_diem),
            }
        )

    # Materials
    mat_total = Decimal("0")
    mat_count = 0
    for m in project.materials or []:
        qty = Decimal(str(m.get("qty", 0)))
        unit = Decimal(str(m.get("unit_cost", 0)))
        mat_total += _round(qty * unit)
        mat_count += 1
    if mat_total > 0:
        lines.append(
            {
                "key": "materials",
                "label": "Materials",
                "detail": f"{mat_count} line item(s)",
                "amount": float(mat_total),
            }
        )

    subtotal = sum(Decimal(str(l["amount"])) for l in lines)
    contingency = _round(subtotal * Decimal(project.contingency_pct) / Decimal("100"))
    after_contingency = subtotal + contingency
    margin = _round(after_contingency * Decimal(project.margin_pct) / Decimal("100"))
    total_ex_vat = after_contingency + margin
    vat = _round(total_ex_vat * Decimal(project.vat_pct) / Decimal("100"))
    total_inc_vat = total_ex_vat + vat

    return {
        "lines": lines,
        "subtotal": float(_round(subtotal)),
        "contingency": float(contingency),
        "margin": float(margin),
        "total_ex_vat": float(_round(total_ex_vat)),
        "vat": float(vat),
        "total_inc_vat": float(_round(total_inc_vat)),
    }
