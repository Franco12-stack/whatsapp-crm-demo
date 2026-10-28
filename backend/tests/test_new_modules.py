"""Coverage for the modules added after the first pass: support tickets,
calls, appointments, goals, promotions, products, reassignment, follow-ups,
and the AI suggestion stub. Not exhaustive per endpoint - focused on the
behaviors that would actually break something (role scoping, state
transitions) rather than restating CRUD.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.db.models import utcnow

from .conftest import make_conversation, token_for

pytestmark = pytest.mark.asyncio(loop_scope="session")


# --------------------------------------------------------------- support ---

async def test_agent_only_sees_their_own_tickets(client, db, agent, admin):
    headers_agent = await token_for(client, agent)
    await client.post(
        "/api/v1/support", json={"title": "Can't log in", "description": "Password reset loop", "priority": "high"},
        headers=headers_agent,
    )

    headers_admin = await token_for(client, admin)
    await client.post(
        "/api/v1/support", json={"title": "Other ticket", "description": "Not mine", "priority": "low"},
        headers=headers_admin,
    )

    response = await client.get("/api/v1/support", headers=headers_agent)
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["title"] == "Can't log in"


async def test_only_admin_can_move_a_ticket(client, db, agent):
    headers = await token_for(client, agent)
    created = await client.post(
        "/api/v1/support", json={"title": "Bug", "description": "Something broke somewhere", "priority": "medium"},
        headers=headers,
    )
    ticket_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/support/{ticket_id}", json={"state": "resolved"}, headers=headers
    )
    assert response.status_code == 403


# ----------------------------------------------------------------- calls ---

async def test_logging_a_call_shows_up_in_history(client, db, agent, line):
    convo = await make_conversation(db, line, warm=True)
    headers = await token_for(client, agent)

    log = await client.post(f"/api/v1/conversations/{convo.id}/calls", headers=headers)
    assert log.status_code == 201
    assert log.json()["duration_seconds"] > 0

    history = await client.get(f"/api/v1/conversations/{convo.id}/calls", headers=headers)
    assert len(history.json()) == 1


# ------------------------------------------------------------ follow-ups ---

async def test_follow_ups_only_lists_stale_warm_conversations(client, db, agent, line):
    fresh = await make_conversation(db, line, warm=True)
    stale = await make_conversation(db, line, warm=True)
    stale.last_message_at = utcnow() - timedelta(days=5)
    cold = await make_conversation(db, line, warm=False)
    cold.last_message_at = utcnow() - timedelta(days=5)
    await db.commit()

    headers = await token_for(client, agent)
    response = await client.get("/api/v1/conversations/follow-ups", headers=headers)
    ids = {c["id"] for c in response.json()}

    assert str(stale.id) in ids
    assert str(fresh.id) not in ids
    assert str(cold.id) not in ids  # cold conversations aren't "follow-ups", they're outreach


# ------------------------------------------------------------- admin/lines

async def test_supervisor_can_list_lines_but_not_edit_them(client, db, supervisor, line):
    headers = await token_for(client, supervisor)

    listing = await client.get("/api/v1/admin/lines", headers=headers)
    assert listing.status_code == 200
    assert any(l["id"] == str(line.id) for l in listing.json())

    edit = await client.patch(
        f"/api/v1/admin/lines/{line.id}/policy",
        json={"policy_daily": 1, "policy_hourly": 1, "policy_new_chats_daily": 1},
        headers=headers,
    )
    assert edit.status_code == 403


# ------------------------------------------------------------- reassign ---

async def test_reassign_moves_the_conversation_to_the_new_line(client, db, admin, agent, line):
    import uuid
    from app.db.models import WhatsAppLine

    convo = await make_conversation(db, line, warm=True)
    other_agent_headers = await token_for(client, admin)  # admin just needs to exist; line owner is separate

    other_line = WhatsAppLine(
        id=uuid.uuid4(), phone_number="+1 555 999 0099", label="Other line",
        policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
    )
    db.add(other_line)
    await db.commit()

    response = await client.patch(
        f"/api/v1/conversations/{convo.id}/reassign", json={"line_id": str(other_line.id)},
        headers=other_agent_headers,
    )
    assert response.status_code == 200
    assert response.json()["line_id"] == str(other_line.id)


async def test_an_agent_cannot_reassign(client, db, agent, line):
    convo = await make_conversation(db, line, warm=True)
    headers = await token_for(client, agent)

    response = await client.patch(
        f"/api/v1/conversations/{convo.id}/reassign", json={"line_id": str(line.id)}, headers=headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------- goals ---

async def test_goal_progress_is_computed_not_stored(client, db, admin, agent, line):
    headers_admin = await token_for(client, admin)
    await client.put(
        f"/api/v1/goals/{agent.id}",
        json={"target_messages_month": 10, "target_conversations_month": 5},
        headers=headers_admin,
    )

    convo = await make_conversation(db, line, warm=True)
    from app.db.models import Message
    db.add(Message(conversation_id=convo.id, direction="outbound", body="hi", sent_by_user_id=agent.id))
    await db.commit()

    response = await client.get("/api/v1/goals", headers=headers_admin)
    goal = next(g for g in response.json() if g["agent_id"] == str(agent.id))
    assert goal["progress_messages"] >= 1


# ------------------------------------------------------- promotions/products

async def test_only_admin_creates_promotions(client, db, agent):
    headers = await token_for(client, agent)
    response = await client.post(
        "/api/v1/promotions", json={"title": "x", "body": "y", "active": True}, headers=headers
    )
    assert response.status_code == 403


async def test_agent_can_read_products_but_not_create(client, db, agent):
    headers = await token_for(client, agent)
    listing = await client.get("/api/v1/products", headers=headers)
    assert listing.status_code == 200

    creation = await client.post(
        "/api/v1/products", json={"name": "Widget", "price_cents": 100, "stock": 5}, headers=headers
    )
    assert creation.status_code == 403


# ------------------------------------------------------------------- ai ---

async def test_ai_suggest_needs_an_inbound_message_first(client, db, agent, line):
    convo = await make_conversation(db, line, warm=False)
    headers = await token_for(client, agent)

    response = await client.post(
        "/api/v1/ai/suggest", json={"conversation_id": str(convo.id)}, headers=headers
    )
    assert response.status_code == 404


async def test_ai_suggest_matches_a_keyword(client, db, agent, line):
    from app.db.models import Message

    convo = await make_conversation(db, line, warm=True)
    db.add(Message(conversation_id=convo.id, direction="inbound", body="What's the price for 10 units?"))
    await db.commit()
    headers = await token_for(client, agent)

    response = await client.post(
        "/api/v1/ai/suggest", json={"conversation_id": str(convo.id)}, headers=headers
    )
    assert response.status_code == 200
    assert "price" in response.json()["suggestion"].lower()
    assert "demo mode" in response.json()["note"].lower()
