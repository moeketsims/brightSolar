"""Post-project reconciliation: compare quoted vs actual and surface learning suggestions."""

from decimal import Decimal

from app.costing import compute_breakdown
from app.models import Expense, Project, ProjectStatus, Settings, Technician, Vehicle
from app.schemas import (
    ActivityAccuracy,
    LearningSuggestion,
    ReconciliationLine,
    ReconciliationOut,
)


CLOSED_STATUSES = {ProjectStatus.COMPLETED, ProjectStatus.INVOICED, ProjectStatus.PAID, ProjectStatus.LOST}


# Mapping from quote-line key → expense category that consumed it
_KEY_TO_CATEGORY: dict[str, list[str]] = {
    "diesel": ["diesel"],
    "vehicle_wear": [],  # no direct expense category; vehicle wear is a sinking fund
    "labour": ["labour"],
    "lodging": ["lodging"],
    "per_diem": ["meals"],
    "materials": ["materials"],
}


def _round(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"))


def build_reconciliation(
    project: Project,
    vehicle: Vehicle | None,
    technicians_by_id: dict[int, Technician],
    settings: Settings,
) -> ReconciliationOut:
    # Recompute the breakdown so we have the same per-line numbers as the stored quote
    bd = compute_breakdown(project, vehicle, technicians_by_id)

    # Group actual expenses by category
    by_cat: dict[str, Decimal] = {}
    for e in project.expenses:
        amt = Decimal(e.amount)
        by_cat[e.category.value] = by_cat.get(e.category.value, Decimal("0")) + amt
    total_actual = sum(by_cat.values(), Decimal("0"))

    # Labour actual = sum over closed time entries × tech rate (hourly)
    labour_actual = Decimal("0")
    for a in project.activities:
        for te in a.time_entries:
            if te.hours is None:
                continue
            tech = technicians_by_id.get(te.technician_id)
            if not tech:
                continue
            # For this MVP: use hourly_rate for everyone (time entries are hour-based)
            rate = Decimal(tech.hourly_rate)
            labour_actual += Decimal(te.hours) * rate

    # Vehicle wear "actual" = same R/km × km — treated as a fund, not a receipt
    vehicle_wear_actual = Decimal("0")
    if vehicle is not None:
        total_km = Decimal(project.one_way_distance_km or 0) * Decimal(project.return_trips or 0) * 2
        vehicle_wear_actual = _round(total_km * Decimal(vehicle.running_cost_per_km or 0))

    derived_actual: dict[str, Decimal] = {
        "labour": labour_actual,
        "vehicle_wear": vehicle_wear_actual,
    }

    # Per-line reconciliation
    lines: list[ReconciliationLine] = []
    consumed_cats: set[str] = set()
    for l in bd["lines"]:
        cats = _KEY_TO_CATEGORY.get(l["key"], [])
        actual = Decimal("0")
        for c in cats:
            actual += by_cat.get(c, Decimal("0"))
            consumed_cats.add(c)
        # Override with derived actuals for labour / vehicle wear
        if l["key"] in derived_actual:
            actual = derived_actual[l["key"]]
        quoted = Decimal(str(l["amount"]))
        delta = actual - quoted
        pct = float((actual / quoted) if quoted > 0 else Decimal("0"))
        lines.append(
            ReconciliationLine(
                key=l["key"],
                label=l["label"],
                quoted=_round(quoted),
                actual=_round(actual),
                delta=_round(delta),
                pct_of_quoted=pct,
            )
        )

    # Catch any "other" actual categories that have no quoted line
    leftover_total = Decimal("0")
    for cat, amt in by_cat.items():
        if cat not in consumed_cats:
            leftover_total += amt
    if leftover_total > 0:
        lines.append(
            ReconciliationLine(
                key="_uncategorised",
                label="Other (tolls, equipment hire, etc.)",
                quoted=Decimal("0"),
                actual=_round(leftover_total),
                delta=_round(leftover_total),
                pct_of_quoted=0.0,
            )
        )

    # Activity-hour accuracy
    accuracy: list[ActivityAccuracy] = []
    total_est = Decimal("0")
    total_actual_hours = Decimal("0")
    for a in project.activities:
        est = Decimal(a.estimated_hours or 0)
        # Sum actual hours across all closed time entries
        actual_h = Decimal("0")
        for te in a.time_entries:
            if te.hours is not None:
                actual_h += Decimal(te.hours)
        total_est += est
        total_actual_hours += actual_h
        accuracy.append(
            ActivityAccuracy(
                activity_id=a.id,
                title=a.title,
                estimated_hours=est,
                actual_hours=_round(actual_h),
                delta_hours=_round(actual_h - est),
                status=a.status.value if hasattr(a.status, "value") else a.status,
            )
        )

    # Overall margin
    quoted_total_ex_vat = Decimal(project.quoted_total_ex_vat or 0)
    margin_quoted = Decimal(str(bd["margin"])) + Decimal(str(bd["contingency"]))
    # realised margin = quoted_ex_vat − (receipt spend + derived labour + derived vehicle wear)
    total_spend = total_actual + labour_actual + vehicle_wear_actual
    margin_realised = quoted_total_ex_vat - total_spend
    margin_delta = margin_realised - margin_quoted

    # Suggestions
    suggestions: list[LearningSuggestion] = []

    # Lodging rate drift
    lodging_actual = by_cat.get("lodging", Decimal("0"))
    nights = Decimal(project.overnight_nights or 0)
    people = Decimal(project.people_on_site or 0)
    nights_x_people = nights * people
    if nights_x_people > 0 and lodging_actual > 0:
        seen_rate = _round(lodging_actual / nights_x_people)
        current = Decimal(settings.default_lodging_per_night)
        if current > 0:
            drift = abs(seen_rate - current) / current
            if drift > Decimal("0.10"):
                suggestions.append(
                    LearningSuggestion(
                        id=f"lodging_rate_{project.id}",
                        summary=f"Observed lodging ran at R{seen_rate}/night (default R{current}). Update default?",
                        field="default_lodging_per_night",
                        target="settings",
                        suggested_value=seen_rate,
                        current_value=current,
                    )
                )

    # Per-diem (meals) drift
    meals_actual = by_cat.get("meals", Decimal("0"))
    if nights_x_people > 0 and meals_actual > 0:
        seen_rate = _round(meals_actual / nights_x_people)
        current = Decimal(settings.default_per_diem)
        if current > 0:
            drift = abs(seen_rate - current) / current
            if drift > Decimal("0.15"):
                suggestions.append(
                    LearningSuggestion(
                        id=f"per_diem_{project.id}",
                        summary=f"Per-diem (meals) ran at R{seen_rate}/person/night (default R{current}). Update?",
                        field="default_per_diem",
                        target="settings",
                        suggested_value=seen_rate,
                        current_value=current,
                    )
                )

    # Diesel rand-per-km drift
    if vehicle is not None:
        total_km = Decimal(project.one_way_distance_km or 0) * Decimal(project.return_trips or 0) * 2
        diesel_actual = by_cat.get("diesel", Decimal("0"))
        if total_km > 0 and diesel_actual > 0:
            seen_rand_per_km = _round(diesel_actual / total_km)
            expected = _round(
                Decimal(vehicle.fuel_consumption_l_per_100km)
                / Decimal("100")
                * Decimal(project.diesel_price_snapshot or 0)
            )
            if expected > 0:
                drift = abs(seen_rand_per_km - expected) / expected
                if drift > Decimal("0.08"):
                    # Back-solve the L/100km using the quoted diesel price (assumes price snap was right)
                    price = Decimal(project.diesel_price_snapshot or 0)
                    if price > 0:
                        implied_l_per_100km = _round(
                            (diesel_actual / price) / total_km * Decimal("100")
                        )
                        current_l = Decimal(vehicle.fuel_consumption_l_per_100km)
                        if abs(implied_l_per_100km - current_l) / current_l > Decimal("0.05"):
                            suggestions.append(
                                LearningSuggestion(
                                    id=f"vehicle_fuel_{vehicle.id}_{project.id}",
                                    summary=f"{vehicle.name}: diesel implies {implied_l_per_100km} L/100km (default {current_l}). Update vehicle?",
                                    field="fuel_consumption_l_per_100km",
                                    target=f"vehicle:{vehicle.id}",
                                    suggested_value=implied_l_per_100km,
                                    current_value=current_l,
                                )
                            )

    return ReconciliationOut(
        project_id=project.id,
        ready=project.status in CLOSED_STATUSES,
        quoted_total_ex_vat=quoted_total_ex_vat,
        actual_total=_round(total_actual),
        margin_quoted=_round(margin_quoted),
        margin_realised=_round(margin_realised),
        margin_delta=_round(margin_delta),
        total_hours_estimated=_round(total_est),
        total_hours_actual=_round(total_actual_hours),
        lines=lines,
        activity_accuracy=accuracy,
        suggestions=suggestions,
    )
