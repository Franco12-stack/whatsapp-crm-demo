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

import random
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, SupervisorUser
from app.db.models import Alert, CallLog, Conversation, Message, User, WhatsAppLine, utcnow
from app.schemas import CallLogOut, ConversationOut, MessageOut, ReassignIn, SendMessageIn
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


@router.get("/follow-ups", response_model=list[ConversationOut])
async def list_follow_ups(user: CurrentUser, db: DbSession) -> list[ConversationOut]:
    """"Contactar hoy": warm conversations that have gone quiet for 2+ days -
    the ones worth a nudge before the lead goes cold for good. Cold
    conversations aren't included here on purpose: reaching out to someone
    who's never replied is a broadcast/outreach decision, not a follow-up."""
    cutoff = utcnow() - timedelta(days=2)
    stmt = (
        select(Conversation)
        .where(Conversation.first_inbound_at.is_not(None), Conversation.last_message_at < cutoff)
        .order_by(Conversation.last_message_at)
    )
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


@router.get("/{conversation_id}/calls", response_model=list[CallLogOut])
async def list_calls(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[CallLogOut]:
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    await _line_for(db, user, conversation)
    rows = (
        await db.execute(
            select(CallLog)
            .where(CallLog.conversation_id == conversation_id)
            .order_by(CallLog.created_at.desc())
        )
    ).scalars().all()
    return [CallLogOut.model_validate(c) for c in rows]


@router.post("/{conversation_id}/calls", response_model=CallLogOut, status_code=status.HTTP_201_CREATED)
async def log_call(conversation_id: uuid.UUID, user: CurrentUser, db: DbSession) -> CallLogOut:
    """Stands in for a telephony/PBX integration: there's no real call, but
    logging one (with a plausible random duration) against the conversation
    is the part worth showing - the pattern of "a chat tool that also tracks
    the calls made about it," not a specific cloud phone vendor's API."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    await _line_for(db, user, conversation)

    call = CallLog(
        conversation_id=conversation_id, user_id=user.id,
        duration_seconds=random.randint(25, 420),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return CallLogOut.model_validate(call)


@router.patch("/{conversation_id}/reassign", response_model=ConversationOut)
async def reassign_conversation(
    conversation_id: uuid.UUID, payload: ReassignIn, _: SupervisorUser, db: DbSession
) -> ConversationOut:
    """Moves a conversation to another agent's line - used from the
    "Repartir" page to rebalance an overloaded agent's queue, or to hand off
    a chat when someone's out. Admin/supervisor only: an agent reassigning
    their own work away is a team-management decision, not a chat action."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    target_line = await db.get(WhatsAppLine, payload.line_id)
    if not target_line:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target line not found")

    conversation.line_id = target_line.id
    await db.commit()
    await db.refresh(conversation, attribute_names=["contact"])
    return ConversationOut(
        id=conversation.id, contact=conversation.contact, line_id=conversation.line_id,
        is_warm=conversation.is_warm, last_message_at=conversation.last_message_at,
    )
