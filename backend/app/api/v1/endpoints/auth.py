from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from typing import Annotated

from fastapi import Depends

from app.core.deps import DbSession
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.schemas import LoginOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> LoginOut:
    user = (
        await db.execute(select(User).where(User.email == form.username))
    ).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    token = create_access_token(user.id, user.role)
    return LoginOut(access_token=token, user=UserOut.model_validate(user))
