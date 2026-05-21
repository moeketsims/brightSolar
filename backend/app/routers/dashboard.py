from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Expense, Job, JobStatus
from app.priority import compute_priority_score
from app.schemas import DashboardStats, JobListItem, JobOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
async def stats(session: AsyncSession = Depends(get_session)):
    today = date.today()
    month_start = today.replace(day=1)

    jobs_res = await session.execute(
        select(Job).options(selectinload(Job.client), selectinload(Job.expenses))
    )
    jobs = jobs_res.scalars().all()

    open_jobs = sum(1 for j in jobs if j.status in (JobStatus.NEW, JobStatus.SCHEDULED, JobStatus.IN_PROGRESS))
    jobs_today = sum(1 for j in jobs if j.scheduled_date == today)

    revenue = sum(
        (Decimal(j.actual_revenue or 0) for j in jobs if j.completed_at and j.completed_at.date() >= month_start),
        Decimal("0"),
    )

    exp_res = await session.execute(select(Expense).where(Expense.incurred_on >= month_start))
    expenses_month = sum(
        (Decimal(e.amount) * Decimal(e.quantity) for e in exp_res.scalars().all()),
        Decimal("0"),
    )

    items: list[JobListItem] = []
    for j in jobs:
        if j.status in (JobStatus.DONE, JobStatus.CANCELLED):
            continue
        total_exp = sum((Decimal(e.amount) * Decimal(e.quantity) for e in j.expenses), Decimal("0"))
        profit = Decimal(j.actual_revenue or 0) - total_exp
        items.append(
            JobListItem(
                **JobOut.model_validate(j).model_dump(),
                client_name=j.client.name,
                total_expenses=total_exp,
                profit=profit,
                priority_score=compute_priority_score(j, total_exp),
            )
        )
    items.sort(key=lambda x: x.priority_score, reverse=True)

    return DashboardStats(
        open_jobs=open_jobs,
        jobs_today=jobs_today,
        revenue_this_month=revenue,
        expenses_this_month=expenses_month,
        profit_this_month=revenue - expenses_month,
        top_priority=items[:5],
    )
