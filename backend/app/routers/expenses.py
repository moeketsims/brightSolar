import os
import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Expense, ExpenseCategory, Project
from app.ocr import extract_amount_from_bytes
from app.schemas import ExpenseOut

router = APIRouter(prefix="/expenses", tags=["expenses"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}


@router.post("", response_model=ExpenseOut, status_code=201)
async def create_expense(
    project_id: int = Form(...),
    category: ExpenseCategory = Form(...),
    amount: Decimal = Form(...),
    description: str | None = Form(None),
    technician_id: int | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    idempotency_key: str | None = Form(None),
    receipt: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
):
    # Idempotency: if the same key has already created an expense, return it (no dupe on retry)
    if idempotency_key:
        existing = await session.execute(
            select(Expense).where(Expense.idempotency_key == idempotency_key)
        )
        dup = existing.scalar_one_or_none()
        if dup:
            return dup

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(400, "Project not found")

    receipt_path: str | None = None
    if receipt is not None and receipt.filename:
        if receipt.content_type and receipt.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, f"Unsupported image type: {receipt.content_type}")
        ext = Path(receipt.filename).suffix.lower() or ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_DIR / safe_name
        content = await receipt.read()
        dest.write_bytes(content)
        receipt_path = f"/uploads/{safe_name}"

    e = Expense(
        project_id=project_id,
        category=category,
        amount=amount,
        description=description,
        technician_id=technician_id,
        latitude=latitude,
        longitude=longitude,
        receipt_path=receipt_path,
        idempotency_key=idempotency_key,
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    return e


@router.get("", response_model=list[ExpenseOut])
async def list_expenses(
    project_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Expense).order_by(Expense.incurred_at.desc())
    if project_id is not None:
        stmt = stmt.where(Expense.project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


class OcrResult(BaseModel):
    amount: Decimal | None


@router.post("/ocr", response_model=OcrResult)
async def ocr_receipt(receipt: UploadFile = File(...)):
    """Run OCR on an uploaded image and return the probable total amount (for auto-fill)."""
    if receipt.content_type and receipt.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {receipt.content_type}")
    data = await receipt.read()
    amt = extract_amount_from_bytes(data)
    return OcrResult(amount=amt)


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(expense_id: int, session: AsyncSession = Depends(get_session)):
    e = await session.get(Expense, expense_id)
    if not e:
        raise HTTPException(404, "Expense not found")
    if e.receipt_path:
        try:
            fname = e.receipt_path.rsplit("/", 1)[-1]
            (UPLOAD_DIR / fname).unlink(missing_ok=True)
        except Exception:
            pass
    await session.delete(e)
    await session.commit()
