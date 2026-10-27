"""Bulk sends, with the cold/warm contact rule baked in.

A "cold" contact is one who has never written to this line first -
`Conversation.first_inbound_at is None`. Opening dozens of cold
conversations in one shot is one of the clearest spam signals there is, so
by default a broadcast silently skips them and reports who got left out, so
the agent can follow up individually. `force=True` sends to everyone anyway
and raises a supervisor alert, because sometimes the agent knows something
the system doesn't (a phone call happened off-platform, say) - the point is
visibility, not a hard wall.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Conversation, Message, utcnow


@dataclass
class BroadcastResult:
    sent_to: list[uuid.UUID]
    skipped_cold: list[dict]  # [{conversation_id, contact_name, phone_number}]


class BroadcastService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send(
        self,
        *,
        conversation_ids: list[uuid.UUID],
        body: str,
        sent_by_user_id: uuid.UUID,
        force: bool = False,
    ) -> BroadcastResult:
        rows = (
            await self.db.execute(
                select(Conversation).where(Conversation.id.in_(conversation_ids))
            )
        ).scalars().all()

        targets, skipped = [], []
        for convo in rows:
            if convo.is_warm or force:
                targets.append(convo)
            else:
                await self.db.refresh(convo, attribute_names=["contact"])
                skipped.append(
                    {
                        "conversation_id": str(convo.id),
                        "contact_name": convo.contact.name,
                        "phone_number": convo.contact.phone_number,
                    }
                )

        for convo in targets:
            self.db.add(
                Message(
                    id=uuid.uuid4(),
                    conversation_id=convo.id,
                    direction="outbound",
                    body=body,
                    sent_by_user_id=sent_by_user_id,
                )
            )
            convo.last_message_at = utcnow()

        forced_cold = force and any(not c.is_warm for c in targets)
        if forced_cold:
            self.db.add(
                Alert(
                    kind="cold_broadcast_forced",
                    title="A broadcast was forced to cold contacts",
                    detail=f"{sum(1 for c in targets if not c.is_warm)} cold contact(s) included by override.",
                    user_id=sent_by_user_id,
                )
            )

        await self.db.flush()
        return BroadcastResult(sent_to=[c.id for c in targets], skipped_cold=skipped)
