from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Client, Expense, Job, JobStatus
from app.priority import compute_priority_score
from app.schemas import JobCreate, JobDetail, JobListItem, JobOut, JobUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _totals(job: Job) -> tuple[Decimal, Decimal]:
    total_exp = sum((Decimal(e.amount) * Decimal(e.quantity) for e in job.expenses), Decimal("0"))
    profit = Decimal(job.actual_revenue or 0) - total_exp
    return total_exp, profit


@router.get("", response_model=list[JobListItem])
async def list_jobs(
    status: JobStatus | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Job).options(selectinload(Job.client), selectinload(Job.expenses))
    if status:
        stmt = stmt.where(Job.status == status)
    result = await session.execute(stmt)
    jobs = result.scalars().all()

    items: list[JobListItem] = []
    for job in jobs:
        total_exp, profit = _totals(job)
        items.append(
            JobListItem(
                **JobOut.model_validate(job).model_dump(),
                client_name=job.client.name,
                total_expenses=total_exp,
                profit=profit,
                priority_score=compute_priority_score(job, total_exp),
            )
        )
    items.sort(key=lambda j: j.priority_score, reverse=True)
    return items


@router.post("", response_model=JobOut, status_code=201)
async def create_job(payload: JobCreate, session: AsyncSession = Depends(get_session)):
    client = await session.get(Client, payload.client_id)
    if not client:
        raise HTTPException(400, "Client not found")
    job = Job(**payload.model_dump())
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Job)
        .options(selectinload(Job.client), selectinload(Job.expenses))
        .where(Job.id == job_id)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    total_exp, profit = _totals(job)
    return JobDetail(
        **JobOut.model_validate(job).model_dump(),
        client=job.client,
        expenses=job.expenses,
        total_expenses=total_exp,
        profit=profit,
        priority_score=compute_priority_score(job, total_exp),
    )


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(job_id: int, payload: JobUpdate, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(job, k, v)
    await session.commit()
    await session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    await session.delete(job)
    await session.commit()
