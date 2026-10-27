"""Supervisor dashboard: live status per agent, and the alert feed.

The usage percentage shown here is deliberately computed against the
*effective* limit (policy capped by warm-up), not the raw commercial policy
- otherwise a freshly connected line looks nearly idle right up until it
hard-stops, which is the exact confusion this demo's source project hit in
production.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import DbSession, SupervisorUser
from app.db.models import Alert, Conversation, Message, User, WhatsAppLine, utcnow
from app.schemas import AgentStatusOut, AlertOut, LineOut, UserOut
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/agents", response_model=list[AgentStatusOut])
async def agent_status(_: SupervisorUser, db: DbSession) -> list[AgentStatusOut]:
    agents = (
        await db.execute(select(User).where(User.role == "agent", User.is_active.is_(True)))
    ).scalars().all()
    limiter = RateLimiter(db)
    day_ago = utcnow() - timedelta(hours=24)

    out: list[AgentStatusOut] = []
    for agent in agents:
        line = (
            await db.execute(select(WhatsAppLine).where(WhatsAppLine.agent_id == agent.id))
        ).scalar_one_or_none()

        line_out = None
        if line:
            limits = limiter._effective(line)  # internal, dashboard-only use
            line_out = LineOut(
                **LineOut.model_validate(line).model_dump(exclude={"usage_percent", "effective_daily_limit", "days_connected"}),
                usage_percent=await limiter.usage_percent(line),
                effective_daily_limit=limits.daily,
                days_connected=limits.days_connected,
            )

        open_conversations = 0
        messages_today = 0
        if line:
            open_conversations = await db.scalar(
                select(func.count(Conversation.id)).where(Conversation.line_id == line.id)
            ) or 0
            messages_today = await db.scalar(
                select(func.count(Message.id))
                .select_from(Message)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Conversation.line_id == line.id,
                    Message.direction == "outbound",
                    Message.sent_at >= day_ago,
                )
            ) or 0

        out.append(
            AgentStatusOut(
                user=UserOut.model_validate(agent),
                line=line_out,
                open_conversations=open_conversations or 0,
                messages_today=messages_today or 0,
            )
        )
    return out


@router.get("/alerts", response_model=list[AlertOut])
async def alerts(_: SupervisorUser, db: DbSession) -> list[AlertOut]:
    rows = (
        await db.execute(
            select(Alert).where(Alert.acknowledged.is_(False)).order_by(Alert.created_at.desc())
        )
    ).scalars().all()
    return [AlertOut.model_validate(a) for a in rows]


@router.post("/alerts/{alert_id}/ack", response_model=AlertOut)
async def ack_alert(alert_id: str, _: SupervisorUser, db: DbSession) -> AlertOut:
    alert = await db.get(Alert, alert_id)
    alert.acknowledged = True
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)
