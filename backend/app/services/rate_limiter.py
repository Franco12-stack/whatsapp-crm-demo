"""Anti-ban rate limiting with a warm-up ramp.

The problem this solves: WhatsApp bans numbers that look automated, and
"automated" mostly means *sudden volume on a number with no history*. A
brand-new number sending 250 messages on day one reads exactly like spam,
even if a human is typing every single one.

The fix is a ramp. A freshly linked number starts with a low ceiling and
grows into its real policy over about a month:

    days connected -> (daily messages, hourly messages, new chats/day)

Two numbers can have the *same* commercial policy (say, 250/day) and behave
completely differently: one that connected an hour ago is capped at 20/day
regardless of policy, one that's been running three months obeys the policy
as-is. The number actually enforced is always

    effective = min(commercial_policy, warm_up_tier_for(days_connected))

That `min()` is the whole idea. Nothing about it is specific to any one
business - it generalizes to any system that sends messages through an
account a platform can silently revoke.

A second design decision, easy to miss: going over the limit does **not**
block the send. It lets the message through and raises an alert for a
supervisor instead. A hard block stops the sale, not the ban - the actual
risk is driven by aggregate volume and how many conversations are cold
opens, not by any single message. Blocking protects nobody and just loses
the customer. See `RateLimitDecision` below and how the conversations
endpoint uses it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, WhatsAppLine

# (days_connected_at_least, daily_limit, hourly_limit, new_chats_per_day)
# Ramps up over ~30 days. Tune the tiers, not the mechanism, per business.
WARM_UP_TIERS: list[tuple[int, int, int, int]] = [
    (0, 20, 8, 3),
    (3, 40, 12, 8),
    (7, 70, 15, 15),
    (14, 100, 18, 20),
    (21, 130, 20, 25),
    (30, 10_000, 10_000, 10_000),  # fully warmed up: policy alone governs
]


def _warm_up_tier(days_connected: int) -> tuple[int, int, int]:
    daily, hourly, new_chats = WARM_UP_TIERS[0][1:]
    for threshold, d, h, n in WARM_UP_TIERS:
        if days_connected >= threshold:
            daily, hourly, new_chats = d, h, n
    return daily, hourly, new_chats


@dataclass
class EffectiveLimits:
    daily: int
    hourly: int
    new_chats_daily: int
    days_connected: int
    warmed_up: bool


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str | None
    limits: EffectiveLimits
    sent_today: int
    sent_last_hour: int


class RateLimiter:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _effective(self, line: WhatsAppLine) -> EffectiveLimits:
        days = (datetime.now(timezone.utc) - line.warmup_started_at).days
        tier_daily, tier_hourly, tier_new = _warm_up_tier(days)
        return EffectiveLimits(
            daily=min(line.policy_daily, tier_daily),
            hourly=min(line.policy_hourly, tier_hourly),
            new_chats_daily=min(line.policy_new_chats_daily, tier_new),
            days_connected=days,
            warmed_up=days >= WARM_UP_TIERS[-1][0],
        )

    async def _counts(self, line_id: uuid.UUID) -> tuple[int, int, int]:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        hour_ago = now - timedelta(hours=1)

        sent_today = await self.db.scalar(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.line_id == line_id,
                Message.direction == "outbound",
                Message.sent_at >= day_ago,
            )
        ) or 0
        sent_last_hour = await self.db.scalar(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.line_id == line_id,
                Message.direction == "outbound",
                Message.sent_at >= hour_ago,
            )
        ) or 0
        new_chats_today = await self.db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.line_id == line_id, Conversation.created_at >= day_ago
            )
        ) or 0
        return sent_today, sent_last_hour, new_chats_today

    async def check(self, line: WhatsAppLine, *, is_new_chat: bool) -> RateLimitDecision:
        limits = self._effective(line)
        sent_today, sent_last_hour, new_chats_today = await self._counts(line.id)

        if sent_today >= limits.daily:
            reason = f"daily limit reached ({limits.daily} msgs/day)"
        elif sent_last_hour >= limits.hourly:
            reason = f"hourly limit reached ({limits.hourly} msgs/hour)"
        elif is_new_chat and new_chats_today >= limits.new_chats_daily:
            reason = f"new-chat limit reached ({limits.new_chats_daily} new chats/day)"
        else:
            reason = None

        return RateLimitDecision(
            allowed=reason is None,
            reason=reason,
            limits=limits,
            sent_today=sent_today,
            sent_last_hour=sent_last_hour,
        )

    async def usage_percent(self, line: WhatsAppLine) -> float:
        """What the dashboard shows. On purpose this is against the
        *effective* limit, not the commercial policy - showing 25% used
        against a policy of 250 is meaningless if the real ceiling right now
        is 40 because the line is still warming up."""
        limits = self._effective(line)
        sent_today, _, _ = await self._counts(line.id)
        if limits.daily <= 0:
            return 0.0
        return round(min(sent_today / limits.daily, 1.0) * 100, 1)
