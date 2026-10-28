"""Metrics: "Mis métricas" (an agent's own numbers) and "Informe" (the
team's, for a supervisor/admin). Same computation, different scope - kept
as one function so the two screens can't drift apart on what counts as
"this week" or what a cold conversation is."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DbSession, SupervisorUser
from app.db.models import (
    BroadcastRun, CallLog, Conversation, Message, SupportTicket, WhatsAppLine, utcnow,
)
from app.schemas import MetricsOut

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def _compute(db: AsyncSession, line_ids: list | None, user_ids: list | None) -> MetricsOut:
    now = utcnow()
    today = now - timedelta(hours=24)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)

    def _msg_count(since):
        stmt = (
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.direction == "outbound", Message.sent_at >= since)
        )
        if line_ids is not None:
            stmt = stmt.where(Conversation.line_id.in_(line_ids))
        return stmt

    messages_today = await db.scalar(_msg_count(today)) or 0
    messages_week = await db.scalar(_msg_count(week)) or 0
    messages_month = await db.scalar(_msg_count(month)) or 0

    convo_stmt = select(Conversation)
    if line_ids is not None:
        convo_stmt = convo_stmt.where(Conversation.line_id.in_(line_ids))
    conversations = (await db.execute(convo_stmt)).scalars().all()
    warm = sum(1 for c in conversations if c.is_warm)

    calls_stmt = select(func.count(CallLog.id))
    if user_ids is not None:
        calls_stmt = calls_stmt.where(CallLog.user_id.in_(user_ids))
    calls = await db.scalar(calls_stmt) or 0

    broadcasts_stmt = select(func.count(BroadcastRun.id))
    if user_ids is not None:
        broadcasts_stmt = broadcasts_stmt.where(BroadcastRun.sent_by_user_id.in_(user_ids))
    broadcasts = await db.scalar(broadcasts_stmt) or 0

    tickets_stmt = select(func.count(SupportTicket.id)).where(SupportTicket.state != "resolved")
    if user_ids is not None:
        tickets_stmt = tickets_stmt.where(SupportTicket.reported_by_user_id.in_(user_ids))
    tickets_open = await db.scalar(tickets_stmt) or 0

    return MetricsOut(
        messages_today=messages_today, messages_this_week=messages_week,
        messages_this_month=messages_month, conversations_total=len(conversations),
        conversations_warm=warm, conversations_cold=len(conversations) - warm,
        calls_logged=calls, broadcasts_sent=broadcasts, tickets_open=tickets_open,
    )


@router.get("/me", response_model=MetricsOut)
async def my_metrics(user: CurrentUser, db: DbSession) -> MetricsOut:
    line = (
        await db.execute(select(WhatsAppLine).where(WhatsAppLine.agent_id == user.id))
    ).scalar_one_or_none()
    line_ids = [line.id] if line else []
    return await _compute(db, line_ids, [user.id])


@router.get("/team", response_model=MetricsOut)
async def team_metrics(_: SupervisorUser, db: DbSession) -> MetricsOut:
    return await _compute(db, None, None)
