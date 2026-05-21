"""Outbound message queue. Client (front-end) enqueues messages. A worker (not
implemented here — run via Celery/cron) picks up queued rows and dispatches to the
configured provider (Meta WhatsApp Business API, SMTP, etc.). For now we just store
them, so the dispatch pipeline is there and the owner sees what WOULD be sent.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Invoice, OutboundMessage, OutboundMessageStatus, Project

router = APIRouter(prefix="/outbound", tags=["outbound"])


class OutboundBase(BaseModel):
    channel: str = "whatsapp"
    to_address: str
    subject: str | None = None
    body: str
    attachment_path: str | None = None
    project_id: int | None = None


class OutboundCreate(OutboundBase):
    pass


class OutboundOut(OutboundBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: OutboundMessageStatus
    provider_message_id: str | None
    error: str | None
    queued_at: datetime
    sent_at: datetime | None


@router.get("", response_model=list[OutboundOut])
async def list_messages(session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(OutboundMessage).order_by(OutboundMessage.queued_at.desc())
    )
    return res.scalars().all()


@router.post("", response_model=OutboundOut, status_code=201)
async def enqueue_message(payload: OutboundCreate, session: AsyncSession = Depends(get_session)):
    msg = OutboundMessage(**payload.model_dump())
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


@router.post("/send-quote/{project_id}", response_model=OutboundOut, status_code=201)
async def enqueue_quote_message(project_id: int, session: AsyncSession = Depends(get_session)):
    """Queue a WhatsApp/email to the client with the quote PDF link."""
    res = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    # Load client
    await session.refresh(project, attribute_names=["client"])
    client = project.client
    to_address = client.phone or client.email or ""
    if not to_address:
        raise HTTPException(400, "Client has no phone or email on file")
    channel = "whatsapp" if client.phone else "email"
    body = (
        f"Good day {client.name},\n\n"
        f"Please find attached our quote ({project.quote_number or 'Q-' + str(project.id)}) for: "
        f"{project.title}.\n"
        f"Valid for 30 days. Let us know if you'd like to proceed or need any changes.\n\n"
        f"Regards,\nBright Solar Power"
    )
    msg = OutboundMessage(
        channel=channel,
        to_address=to_address,
        subject=f"Quote {project.quote_number or ''} — {project.title}",
        body=body,
        attachment_path=f"/projects/{project_id}/quote.pdf",
        project_id=project_id,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


@router.post("/send-invoice/{invoice_id}", response_model=OutboundOut, status_code=201)
async def enqueue_invoice_message(invoice_id: int, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    await session.refresh(inv, attribute_names=["project"])
    await session.refresh(inv.project, attribute_names=["client"])
    client = inv.project.client
    to_address = client.phone or client.email or ""
    if not to_address:
        raise HTTPException(400, "Client has no phone or email on file")
    channel = "whatsapp" if client.phone else "email"
    body = (
        f"Good day {client.name},\n\n"
        f"Attached is invoice {inv.invoice_number} (R{inv.total_inc_vat:,.2f} inc VAT) "
        f"due {inv.due_at.strftime('%d %B %Y')}.\n\n"
        f"Thank you for your business.\nBright Solar Power"
    )
    msg = OutboundMessage(
        channel=channel,
        to_address=to_address,
        subject=f"Invoice {inv.invoice_number}",
        body=body,
        attachment_path=f"/invoices/{invoice_id}/pdf",
        project_id=inv.project_id,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg


@router.patch("/{msg_id}", response_model=OutboundOut)
async def update_message(msg_id: int, status: OutboundMessageStatus, session: AsyncSession = Depends(get_session)):
    """Used by the dispatcher worker to mark a message sent/failed."""
    msg = await session.get(OutboundMessage, msg_id)
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.status = status
    if status in (OutboundMessageStatus.SENT, OutboundMessageStatus.DELIVERED):
        msg.sent_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(msg)
    return msg
