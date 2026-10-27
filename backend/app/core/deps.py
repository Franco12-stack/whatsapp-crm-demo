from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    return user


async def require_supervisor_or_admin(user: CurrentUser) -> User:
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Supervisors only")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
SupervisorUser = Annotated[User, Depends(require_supervisor_or_admin)]
