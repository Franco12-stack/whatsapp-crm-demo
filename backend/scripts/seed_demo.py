"""Populates the database with demo users, three WhatsApp lines at three
different points in the warm-up ramp (so the rate limiter's behavior is
visible immediately), and a batch of conversations - some warm, some cold -
so the broadcast cold/warm split has something to show.

Run with: docker compose exec backend python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import timedelta

from app.core.security import hash_password
from app.db.models import Base, Contact, Conversation, Message, User, WhatsAppLine, utcnow
from app.db.session import SessionLocal, engine

FIRST_NAMES = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew",
               "Jamie", "Avery", "Quinn", "Reese", "Rowan", "Sage", "Skyler"]
LAST_NAMES = ["Johnson", "Lee", "Garcia", "Smith", "Patel", "Nguyen", "Brown", "Kim"]

OPENING_LINES = [
    "Hi! Saw your post about the new collection, is it available?",
    "Hello, I'd like a quote for 20 units.",
    "Hey, do you still have the sample from last week?",
    "Good morning, following up on my order #",
    "Hi there, can I get more details on pricing?",
]

PASSWORD = "demo1234"


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        admin = User(
            id=uuid.uuid4(), full_name="Dana Admin", email="admin@demo.com",
            password_hash=hash_password(PASSWORD), role="admin",
        )
        supervisor = User(
            id=uuid.uuid4(), full_name="Sam Supervisor", email="supervisor@demo.com",
            password_hash=hash_password(PASSWORD), role="supervisor",
        )
        db.add_all([admin, supervisor])

        agents = [
            User(id=uuid.uuid4(), full_name=name, email=email, password_hash=hash_password(PASSWORD), role="agent")
            for name, email in [
                ("Nicole Agent", "nicole@demo.com"),
                ("Marcus Agent", "marcus@demo.com"),
                ("Priya Agent", "priya@demo.com"),
            ]
        ]
        db.add_all(agents)
        await db.flush()

        # Three lines at three different warm-up stages, on purpose:
        #   - just connected -> capped at the lowest tier regardless of policy
        #   - ten days in    -> mid-ramp
        #   - fully warmed   -> obeys the commercial policy as-is
        lines = [
            WhatsAppLine(
                id=uuid.uuid4(), phone_number="+1 555 010 0001", label="Line A - just connected",
                agent_id=agents[0].id, policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
                warmup_started_at=utcnow(),
            ),
            WhatsAppLine(
                id=uuid.uuid4(), phone_number="+1 555 010 0002", label="Line B - warming up (day 10)",
                agent_id=agents[1].id, policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
                warmup_started_at=utcnow() - timedelta(days=10),
            ),
            WhatsAppLine(
                id=uuid.uuid4(), phone_number="+1 555 010 0003", label="Line C - fully warmed up",
                agent_id=agents[2].id, policy_daily=250, policy_hourly=30, policy_new_chats_daily=30,
                warmup_started_at=utcnow() - timedelta(days=45),
            ),
        ]
        db.add_all(lines)
        await db.flush()

        for line in lines:
            n_contacts = random.randint(10, 16)
            for i in range(n_contacts):
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                contact = Contact(
                    id=uuid.uuid4(), name=name,
                    phone_number=f"+1 555 {random.randint(200,999)} {random.randint(1000,9999)}",
                )
                db.add(contact)
                await db.flush()

                is_warm = random.random() < 0.65  # ~2/3 warm, rest cold on purpose
                created = utcnow() - timedelta(days=random.randint(0, 20), hours=random.randint(0, 23))
                conversation = Conversation(
                    id=uuid.uuid4(), contact_id=contact.id, line_id=line.id,
                    first_inbound_at=created if is_warm else None,
                    last_message_at=created, created_at=created,
                )
                db.add(conversation)
                await db.flush()

                if is_warm:
                    opening = random.choice(OPENING_LINES)
                    if opening.endswith("#"):
                        opening += str(1000 + i)
                    db.add(Message(
                        conversation_id=conversation.id, direction="inbound",
                        body=opening,
                        sent_at=created,
                    ))
                    if random.random() < 0.7:
                        db.add(Message(
                            conversation_id=conversation.id, direction="outbound",
                            body="Hi! Yes, let me get that sorted for you.",
                            sent_by_user_id=line.agent_id, sent_at=created + timedelta(minutes=5),
                        ))

        await db.commit()

    print("Seed complete. Demo accounts (all use password: demo1234):")
    print("  admin@demo.com       (admin)")
    print("  supervisor@demo.com  (supervisor)")
    print("  nicole@demo.com      (agent, Line A - just connected)")
    print("  marcus@demo.com      (agent, Line B - warming up)")
    print("  priya@demo.com       (agent, Line C - fully warmed up)")


if __name__ == "__main__":
    asyncio.run(main())
