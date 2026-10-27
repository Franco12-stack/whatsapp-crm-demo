"""Stands in for the real WhatsApp provider (WAHA/the Business API in
production) so the demo runs with no external account, no phone, and no
API key. A background task periodically makes a random open conversation
"reply", so the inbox feels alive during a walkthrough.

This is the one piece of the original system that's intentionally fake -
everything else (rate limiting, roles, broadcasts, alerting) is the real
logic, just generalized away from one company's specifics.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Conversation, Message
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_REPLIES = [
    "Thanks, that works for me!",
    "Can you send the price list again?",
    "What about the blue one, is it in stock?",
    "Perfect, I'll place the order today.",
    "Sorry for the late reply, I was traveling.",
    "Is there a discount for buying 3+?",
    "Got it, talk soon.",
    "Can we do a call tomorrow morning?",
]


async def _simulate_one_reply(db: AsyncSession) -> None:
    convo = (
        await db.execute(
            select(Conversation).order_by(Conversation.last_message_at.desc()).limit(25)
        )
    ).scalars().all()
    if not convo:
        return
    target = random.choice(convo)
    from app.db.models import utcnow

    db.add(
        Message(
            id=uuid.uuid4(),
            conversation_id=target.id,
            direction="inbound",
            body=random.choice(_REPLIES),
        )
    )
    target.last_message_at = utcnow()
    if target.first_inbound_at is None:
        target.first_inbound_at = utcnow()
    await db.flush()


async def run_customer_simulator() -> None:
    """Background loop started from the FastAPI lifespan. Cancelled cleanly
    on shutdown - see app/main.py."""
    if not settings.simulate_customer_replies:
        return
    logger.info("customer simulator started (tick=%ss)", settings.simulator_tick_seconds)
    with contextlib.suppress(asyncio.CancelledError):
        while True:
            await asyncio.sleep(settings.simulator_tick_seconds)
            try:
                async with SessionLocal() as db:
                    await _simulate_one_reply(db)
                    await db.commit()
            except Exception:  # noqa: BLE001 - a demo background task must never crash the app
                logger.exception("customer simulator tick failed")
