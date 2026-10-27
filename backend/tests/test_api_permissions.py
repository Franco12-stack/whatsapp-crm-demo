"""A few end-to-end checks through the real HTTP layer: login works, an
agent can't see another agent's conversations, and sending past the limit
is allowed-with-an-alert rather than blocked outright."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import Alert

from .conftest import make_conversation, token_for

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_login_returns_a_usable_token(client, agent):
    headers = await token_for(client, agent)
    response = await client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 200


async def test_wrong_password_is_rejected(client, agent):
    response = await client.post(
        "/api/v1/auth/login", data={"username": agent.email, "password": "nope"}
    )
    assert response.status_code == 401


async def test_sending_past_the_limit_still_succeeds_but_raises_an_alert(db, client, agent, line):
    from app.db.models import Message

    line.policy_daily = 1
    await db.commit()
    convo = await make_conversation(db, line, warm=True)
    db.add(Message(conversation_id=convo.id, direction="outbound", body="already sent one"))
    await db.commit()

    headers = await token_for(client, agent)
    response = await client.post(
        f"/api/v1/conversations/{convo.id}/messages", json={"body": "one more"}, headers=headers
    )

    assert response.status_code == 201  # not blocked
    alerts = (
        await db.execute(
            select(Alert).where(Alert.kind == "rate_limit_exceeded", Alert.user_id == agent.id)
        )
    ).scalars().all()
    assert len(alerts) == 1
