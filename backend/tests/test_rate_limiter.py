"""The warm-up ramp is the whole point of this project, so it gets the most
coverage: the effective limit always has to be min(policy, warm-up tier),
never just one or the other.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.db.models import utcnow
from app.services.rate_limiter import RateLimiter, _warm_up_tier

from .conftest import make_conversation

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.parametrize(
    "days,expected_daily",
    [(0, 20), (2, 20), (3, 40), (6, 40), (7, 70), (13, 70), (14, 100), (20, 100), (21, 130), (29, 130)],
)
def test_warm_up_tier_steps_match_the_ramp(days, expected_daily):
    daily, _, _ = _warm_up_tier(days)
    assert daily == expected_daily


def test_after_30_days_the_ramp_stops_limiting():
    daily, hourly, new_chats = _warm_up_tier(45)
    assert daily > 1000 and hourly > 1000 and new_chats > 1000


async def test_a_brand_new_line_is_capped_even_with_a_high_policy(db, agent):
    from app.db.models import WhatsAppLine
    import uuid

    brand_new = WhatsAppLine(
        id=uuid.uuid4(), phone_number="+1 555 999 0000", label="Brand new", agent_id=agent.id,
        policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
        warmup_started_at=utcnow(),
    )
    db.add(brand_new)
    await db.flush()

    limits = RateLimiter(db)._effective(brand_new)

    assert limits.daily == 20  # the warm-up tier, not the 250 policy
    assert not limits.warmed_up


async def test_a_fully_warmed_line_obeys_its_own_policy(db, line):
    limits = RateLimiter(db)._effective(line)

    assert limits.daily == line.policy_daily
    assert limits.warmed_up


async def test_a_low_policy_still_wins_over_a_warmed_up_tier(db, agent):
    """The min() has to work both directions: a deliberately throttled line
    (low commercial policy) must stay throttled even once it's fully warm."""
    from app.db.models import WhatsAppLine
    import uuid

    cautious = WhatsAppLine(
        id=uuid.uuid4(), phone_number="+1 555 999 0001", label="Deliberately slow", agent_id=agent.id,
        policy_daily=15, policy_hourly=5, policy_new_chats_daily=2,
        warmup_started_at=utcnow() - timedelta(days=90),
    )
    db.add(cautious)
    await db.flush()

    limits = RateLimiter(db)._effective(cautious)

    assert limits.daily == 15


async def test_check_blocks_once_the_effective_daily_limit_is_reached(db, agent):
    from app.db.models import WhatsAppLine, Message
    import uuid

    line = WhatsAppLine(
        id=uuid.uuid4(), phone_number="+1 555 999 0002", label="Tiny limit", agent_id=agent.id,
        policy_daily=2, policy_hourly=30, policy_new_chats_daily=30,
        warmup_started_at=utcnow() - timedelta(days=90),
    )
    db.add(line)
    await db.flush()
    convo = await make_conversation(db, line, warm=True)

    for _ in range(2):
        db.add(Message(conversation_id=convo.id, direction="outbound", body="hi"))
    await db.flush()

    decision = await RateLimiter(db).check(line, is_new_chat=False)

    assert decision.allowed is False
    assert "daily limit" in decision.reason
