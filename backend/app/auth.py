"""Auth helpers: password hashing, JWT, dependencies."""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import User, UserRole

COOKIE_NAME = "bsp_token"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def token_from_request(request: Request) -> str | None:
    tok = request.cookies.get(COOKIE_NAME)
    if tok:
        return tok
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    # Allow token via query (for PDF links in new tabs if cookie domain misses)
    qtok = request.query_params.get("token")
    return qtok


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _user_from_token(token: str | None, session: AsyncSession) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        return None
    if not user_id:
        return None
    user = await session.get(User, user_id)
    if user and user.active:
        return user
    return None


async def current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    return await _user_from_token(token_from_request(request), session)


async def current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await _user_from_token(token_from_request(request), session)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


def require_roles(*allowed: UserRole):
    async def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in allowed and user.role != UserRole.OWNER:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(r.value for r in allowed)}")
        return user
    return _dep
