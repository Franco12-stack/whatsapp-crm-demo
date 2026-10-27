"""Inbox endpoints.

Two design decisions worth calling out:

1. An admin/supervisor can send inside *any* agent's conversation. The
   message goes out through that agent's WhatsApp line (so the customer
   sees one continuous thread, not a random second number), but it's
   recorded as sent by whoever actually typed it (`sent_by_user_id`).

2. Going over the rate limit never blocks the send - see the module
   docstring in app/services/rate_limiter.py for why. It raises an alert
   instead and lets the message through.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models import Alert, Conversation, Message, User, WhatsAppLine, utcnow
from app.schemas import ConversationOut, MessageOut, SendMessageIn
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _line_for(db: DbSession, user: User, conversation: Conversation) -> WhatsAppLine:
    line = await db.get(WhatsAppLine, conversation.line_id)
    if not line:
        raise HTTPException(status.HTTP_409_CONFLICT, "This conversation has no WhatsApp line")
    if user.role == "agent" and line.agent_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This conversation isn't on your line")
    return line


@router.get("", response_model=list[ConversationOut])
async def list_conversations(user: CurrentUser, db: DbSession) -> list[ConversationOut]:
    stmt = select(Conversation).order_by(Conversation.last_message_at.desc())
    if user.role == "agent":
        stmt = stmt.join(WhatsAppLine, WhatsAppLine.id == Conversation.line_id).where(
            WhatsAppLine.agent_id == user.id
        )
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        await db.refresh(row, attribute_names=["contact"])
    return [
        ConversationOut(
            id=r.id, contact=r.contact, line_id=r.line_id, is_warm=r.is_warm,
            last_message_at=r.last_message_at,
        )
        for r in rows
    ]


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[MessageOut]:
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    await _line_for(db, user, conversation)  # authorization check
    rows = (
        await db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sent_at)
        )
    ).scalars().all()
    return [MessageOut.model_validate(m) for m in rows]


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: uuid.UUID, payload: SendMessageIn, user: CurrentUser, db: DbSession
) -> MessageOut:
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    line = await _line_for(db, user, conversation)

    decision = await RateLimiter(db).check(line, is_new_chat=False)
    if not decision.allowed:
        owner = f"agent {line.agent_id}" if line.agent_id != user.id else "your own line"
        db.add(
            Alert(
                kind="rate_limit_exceeded",
                title=f"{user.full_name} sent past the limit on {owner}",
                detail=decision.reason,
                user_id=line.agent_id or user.id,
            )
        )

    message = Message(
        conversation_id=conversation_id,
        direction="outbound",
        body=payload.body,
        sent_by_user_id=user.id,
    )
    db.add(message)
    conversation.last_message_at = utcnow()
    await db.commit()
    await db.refresh(message)
    return MessageOut.model_validate(message)
