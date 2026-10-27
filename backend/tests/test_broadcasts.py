"""Cold contacts get skipped by default, listed back so the agent can follow
up individually, and only included with an explicit `force` - which raises
an alert instead of silently complying."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Alert
from app.services.broadcasts import BroadcastService

from .conftest import make_conversation

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_cold_contacts_are_skipped_by_default(db, line, agent):
    warm = await make_conversation(db, line, warm=True)
    cold = await make_conversation(db, line, warm=False)

    result = await BroadcastService(db).send(
        conversation_ids=[warm.id, cold.id], body="Sale!", sent_by_user_id=agent.id
    )

    assert result.sent_to == [warm.id]
    assert len(result.skipped_cold) == 1
    assert result.skipped_cold[0]["conversation_id"] == str(cold.id)


async def test_force_sends_to_cold_contacts_and_raises_an_alert(db, line, agent):
    cold = await make_conversation(db, line, warm=False)

    result = await BroadcastService(db).send(
        conversation_ids=[cold.id], body="Sale!", sent_by_user_id=agent.id, force=True
    )

    assert result.sent_to == [cold.id]
    assert result.skipped_cold == []

    alerts = (
        await db.execute(select(Alert).where(Alert.kind == "cold_broadcast_forced", Alert.user_id == agent.id))
    ).scalars().all()
    assert len(alerts) == 1


async def test_a_normal_send_to_only_warm_contacts_raises_no_alert(db, line, agent):
    warm = await make_conversation(db, line, warm=True)

    await BroadcastService(db).send(conversation_ids=[warm.id], body="Hi!", sent_by_user_id=agent.id)

    alerts = (await db.execute(select(Alert).where(Alert.user_id == agent.id))).scalars().all()
    assert alerts == []
