"""Objetivos: a monthly target an admin sets per agent, with progress
computed live (not stored) against this month's messages/conversations."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.db.models import Conversation, Goal, Message, User, WhatsAppLine, utcnow
from app.schemas import GoalIn, GoalOut

router = APIRouter(prefix="/goals", tags=["goals"])


async def _with_progress(db: DbSession, goal: Goal) -> GoalOut:
    line = (
        await db.execute(select(WhatsAppLine).where(WhatsAppLine.agent_id == goal.agent_id))
    ).scalar_one_or_none()
    progress_messages = 0
    progress_conversations = 0
    if line:
        month_ago = utcnow() - timedelta(days=30)
        progress_messages = await db.scalar(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.line_id == line.id, Message.direction == "outbound",
                Message.sent_at >= month_ago,
            )
        ) or 0
        progress_conversations = await db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.line_id == line.id, Conversation.created_at >= month_ago
            )
        ) or 0
    out = GoalOut.model_validate(goal)
    out.progress_messages = progress_messages
    out.progress_conversations = progress_conversations
    return out


@router.get("", response_model=list[GoalOut])
async def list_goals(user: CurrentUser, db: DbSession) -> list[GoalOut]:
    stmt = select(Goal)
    if user.role == "agent":
        stmt = stmt.where(Goal.agent_id == user.id)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _with_progress(db, g) for g in rows]


@router.put("/{agent_id}", response_model=GoalOut)
async def set_goal(agent_id: uuid.UUID, payload: GoalIn, _: AdminUser, db: DbSession) -> GoalOut:
    agent = await db.get(User, agent_id)
    if not agent or agent.role != "agent":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")

    goal = (await db.execute(select(Goal).where(Goal.agent_id == agent_id))).scalar_one_or_none()
    if goal:
        goal.target_messages_month = payload.target_messages_month
        goal.target_conversations_month = payload.target_conversations_month
    else:
        goal = Goal(
            agent_id=agent_id, target_messages_month=payload.target_messages_month,
            target_conversations_month=payload.target_conversations_month,
        )
        db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return await _with_progress(db, goal)
