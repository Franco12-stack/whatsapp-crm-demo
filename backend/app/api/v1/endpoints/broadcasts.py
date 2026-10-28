from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import CurrentUser, DbSession
from app.db.models import BroadcastRun
from app.schemas import BroadcastIn, BroadcastOut, BroadcastRunOut
from app.services.broadcasts import BroadcastService

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.post("", response_model=BroadcastOut)
async def send_broadcast(payload: BroadcastIn, user: CurrentUser, db: DbSession) -> BroadcastOut:
    result = await BroadcastService(db).send(
        conversation_ids=payload.conversation_ids,
        body=payload.body,
        sent_by_user_id=user.id,
        force=payload.force,
    )
    await db.commit()
    return BroadcastOut(sent_to=result.sent_to, skipped_cold=result.skipped_cold)


@router.get("", response_model=list[BroadcastRunOut])
async def list_broadcasts(user: CurrentUser, db: DbSession) -> list[BroadcastRunOut]:
    """Agents only see their own sends; admins and supervisors see the
    team's, since that's the role that needs to spot a pattern across
    people, not just remember their own."""
    stmt = select(BroadcastRun).options(joinedload(BroadcastRun.sent_by)).order_by(
        BroadcastRun.created_at.desc()
    )
    if user.role == "agent":
        stmt = stmt.where(BroadcastRun.sent_by_user_id == user.id)
    rows = (await db.execute(stmt)).scalars().all()
    return [BroadcastRunOut.model_validate(r) for r in rows]
