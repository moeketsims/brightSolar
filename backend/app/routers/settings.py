from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Settings
from app.schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def get_or_create_settings(session: AsyncSession) -> Settings:
    s = await session.get(Settings, 1)
    if not s:
        s = Settings(id=1)
        session.add(s)
        await session.commit()
        await session.refresh(s)
    return s


@router.get("", response_model=SettingsOut)
async def read_settings(session: AsyncSession = Depends(get_session)):
    return await get_or_create_settings(session)


@router.patch("", response_model=SettingsOut)
async def update_settings(payload: SettingsUpdate, session: AsyncSession = Depends(get_session)):
    s = await get_or_create_settings(session)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    await session.commit()
    await session.refresh(s)
    return s
