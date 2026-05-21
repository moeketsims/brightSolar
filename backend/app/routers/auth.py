from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import COOKIE_NAME, create_access_token, current_user, hash_password, require_roles, verify_password
from app.config import settings as app_settings
from app.db import get_session
from app.models import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: UserRole
    active: bool
    technician_id: int | None


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole = UserRole.TECH
    technician_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = None
    technician_id: int | None = None


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=app_settings.env == "production",
        max_age=app_settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(User).where(User.email == payload.email.lower()))
    user = res.scalar_one_or_none()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenOut(access_token=token)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_roles(UserRole.OWNER)),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(User).order_by(User.name))
    return res.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_roles(UserRole.OWNER)),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(User).where(User.email == payload.email.lower()))
    if res.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")
    user = User(
        email=payload.email.lower(),
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        technician_id=payload.technician_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_roles(UserRole.OWNER)),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current: User = Depends(require_roles(UserRole.OWNER)),
    session: AsyncSession = Depends(get_session),
):
    if user_id == current.id:
        raise HTTPException(400, "Cannot delete yourself")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await session.delete(user)
    await session.commit()
