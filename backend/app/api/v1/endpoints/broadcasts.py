from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas import BroadcastIn, BroadcastOut
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
