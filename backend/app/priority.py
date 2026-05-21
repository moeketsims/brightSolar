from decimal import Decimal

from app.models import Job, Urgency

URGENCY_BOOST = {
    Urgency.LOW: 0,
    Urgency.NORMAL: 100,
    Urgency.HIGH: 500,
    Urgency.CRITICAL: 2000,
}

DIESEL_COST_PER_KM = Decimal("3.50")


def compute_priority_score(job: Job, total_expenses: Decimal | None = None) -> float:
    """Score = est_margin - travel_cost + urgency_boost. Higher = do first."""
    if job.priority_override is not None:
        return float(job.priority_override)

    est_margin = Decimal(job.estimated_revenue) - Decimal(job.estimated_cost)
    travel_cost = Decimal(job.distance_km) * DIESEL_COST_PER_KM * 2
    boost = Decimal(URGENCY_BOOST[job.urgency])
    return float(est_margin - travel_cost + boost)
