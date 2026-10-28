"""Admin: manage WhatsApp lines and their policies, and what the original
project called "reset warm-up" - forcing a line back to day zero after it
had to reconnect, without waiting for an automatic signal."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession, SupervisorUser
from app.db.models import WhatsAppLine, utcnow
from app.schemas import LineOut, LinePolicyIn
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/admin", tags=["admin"])


async def _to_out(db: DbSession, line: WhatsAppLine) -> LineOut:
    limiter = RateLimiter(db)
    limits = limiter._effective(line)
    base = LineOut.model_validate(line).model_dump(
        exclude={"usage_percent", "effective_daily_limit", "days_connected"}
    )
    return LineOut(
        **base,
        usage_percent=await limiter.usage_percent(line),
        effective_daily_limit=limits.daily,
        days_connected=limits.days_connected,
    )


@router.get("/lines", response_model=list[LineOut])
async def list_lines(_: SupervisorUser, db: DbSession) -> list[LineOut]:
    """Supervisors can see lines (needed for the Distribute page) but only
    admins can edit a policy or reset a warm-up - see the endpoints below."""
    rows = (await db.execute(select(WhatsAppLine).order_by(WhatsAppLine.label))).scalars().all()
    return [await _to_out(db, line) for line in rows]


@router.patch("/lines/{line_id}/policy", response_model=LineOut)
async def update_policy(
    line_id: uuid.UUID, payload: LinePolicyIn, _: AdminUser, db: DbSession
) -> LineOut:
    line = await db.get(WhatsAppLine, line_id)
    if not line:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Line not found")
    line.policy_daily = payload.policy_daily
    line.policy_hourly = payload.policy_hourly
    line.policy_new_chats_daily = payload.policy_new_chats_daily
    await db.commit()
    await db.refresh(line)
    return await _to_out(db, line)


@router.post("/lines/{line_id}/reset-warmup", response_model=LineOut)
async def reset_warmup(line_id: uuid.UUID, _: AdminUser, db: DbSession) -> LineOut:
    """Use when a line is known to have been banned/reconnected and you don't
    want to wait for that to be detected automatically."""
    line = await db.get(WhatsAppLine, line_id)
    if not line:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Line not found")
    line.warmup_started_at = utcnow()
    await db.commit()
    await db.refresh(line)
    return await _to_out(db, line)
