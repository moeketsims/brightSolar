from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Client
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
async def list_clients(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Client).order_by(Client.name))
    return res.scalars().all()


@router.post("", response_model=ClientOut, status_code=201)
async def create_client(payload: ClientCreate, session: AsyncSession = Depends(get_session)):
    c = Client(**payload.model_dump())
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int, session: AsyncSession = Depends(get_session)):
    c = await session.get(Client, client_id)
    if not c:
        raise HTTPException(404, "Client not found")
    await session.delete(c)
    await session.commit()
