"""Populates every module with demo data: three WhatsApp lines at three
different points in the warm-up ramp, conversations (some warm, some cold,
some gone quiet so "Contactar hoy" has something to show), call logs, a
broadcast history, support tickets in each state, monthly goals, a couple
of promotions, and a small product catalog.

Run with: docker compose exec backend python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import timedelta

from app.core.security import hash_password
from app.db.models import (
    Appointment, Base, BroadcastRun, CallLog, Contact, Conversation, Goal, Message,
    Product, Promotion, SupportTicket, User, WhatsAppLine, utcnow,
)
from app.db.session import SessionLocal, engine

FIRST_NAMES = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew",
               "Jamie", "Avery", "Quinn", "Reese", "Rowan", "Sage", "Skyler"]
LAST_NAMES = ["Johnson", "Lee", "Garcia", "Smith", "Patel", "Nguyen", "Brown", "Kim"]
ACCOUNTS = ["Retail", "Wholesale", "Online store", "Marketplace", "Direct"]

OPENING_LINES = [
    "Hi! Saw your post about the new collection, is it available?",
    "Hello, I'd like a quote for 20 units.",
    "Hey, do you still have the sample from last week?",
    "Good morning, following up on my order #",
    "Hi there, can I get more details on pricing?",
    "Is there a discount for buying 3 or more?",
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

        warm_conversations: list[Conversation] = []

        for line in lines:
            n_contacts = random.randint(10, 16)
            for i in range(n_contacts):
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                contact = Contact(
                    id=uuid.uuid4(), name=name,
                    phone_number=f"+1 555 {random.randint(200,999)} {random.randint(1000,9999)}",
                    crm_account=random.choice(ACCOUNTS),
                    lifetime_value=random.choice([0, 0, 120, 340, 890, 1500, 4200]) * 100,
                    last_order_at=(
                        utcnow() - timedelta(days=random.randint(1, 120))
                        if random.random() < 0.6 else None
                    ),
                )
                db.add(contact)
                await db.flush()

                is_warm = random.random() < 0.65  # ~2/3 warm, rest cold on purpose
                # Some warm conversations go quiet past 2 days on purpose, so
                # "Contactar hoy" (follow-ups) has rows to show.
                days_ago = random.randint(0, 20)
                created = utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
                conversation = Conversation(
                    id=uuid.uuid4(), contact_id=contact.id, line_id=line.id,
                    first_inbound_at=created if is_warm else None,
                    last_message_at=created, created_at=created,
                )
                db.add(conversation)
                await db.flush()

                if is_warm:
                    warm_conversations.append(conversation)
                    opening = random.choice(OPENING_LINES)
                    if opening.endswith("#"):
                        opening += str(1000 + i)
                    db.add(Message(
                        conversation_id=conversation.id, direction="inbound",
                        body=opening, sent_at=created,
                    ))
                    if random.random() < 0.7:
                        db.add(Message(
                            conversation_id=conversation.id, direction="outbound",
                            body="Hi! Yes, let me get that sorted for you.",
                            sent_by_user_id=line.agent_id, sent_at=created + timedelta(minutes=5),
                        ))
        await db.flush()

        # --- Call logs: a handful against warm conversations -------------
        for convo in random.sample(warm_conversations, k=min(6, len(warm_conversations))):
            line = next(l for l in lines if l.id == convo.line_id)
            db.add(CallLog(
                conversation_id=convo.id, user_id=line.agent_id,
                duration_seconds=random.randint(25, 420),
                created_at=convo.last_message_at + timedelta(minutes=random.randint(1, 60)),
            ))

        # --- Broadcast history ---------------------------------------------
        db.add_all([
            BroadcastRun(
                body="New season is live! 20% off this week only.",
                sent_by_user_id=agents[2].id, sent_count=9, skipped_cold_count=4, forced=False,
                created_at=utcnow() - timedelta(days=3),
            ),
            BroadcastRun(
                body="Reminder: your quote expires tomorrow.",
                sent_by_user_id=agents[1].id, sent_count=5, skipped_cold_count=0, forced=False,
                created_at=utcnow() - timedelta(days=1, hours=4),
            ),
        ])

        # --- Support tickets, one per state ---------------------------------
        db.add_all([
            SupportTicket(
                title="Can't send images in chat", description="Tapping the attach button does nothing on mobile.",
                priority="high", state="open", reported_by_user_id=agents[0].id,
                created_at=utcnow() - timedelta(hours=6),
            ),
            SupportTicket(
                title="Warm-up tier looks wrong for Line B", description="Shows day 10 but it should be day 12 by my count.",
                priority="medium", state="in_progress", reported_by_user_id=agents[1].id,
                admin_note="Checking the warmup_started_at value now.",
                created_at=utcnow() - timedelta(days=1),
            ),
            SupportTicket(
                title="Add a dark mode toggle", description="Would be nice to switch to a light theme for daytime use.",
                priority="low", state="resolved", reported_by_user_id=agents[2].id,
                admin_note="Added to the roadmap, not urgent.",
                created_at=utcnow() - timedelta(days=5),
            ),
        ])

        # --- Monthly goals, one per agent ------------------------------------
        db.add_all([
            Goal(agent_id=agents[0].id, target_messages_month=300, target_conversations_month=20),
            Goal(agent_id=agents[1].id, target_messages_month=500, target_conversations_month=40),
            Goal(agent_id=agents[2].id, target_messages_month=800, target_conversations_month=60),
        ])

        # --- Promotions -------------------------------------------------------
        db.add_all([
            Promotion(
                title="Spring sale", active=True,
                body="🌸 Spring sale is here! 20% off everything this week — want me to send details?",
            ),
            Promotion(
                title="New customer welcome", active=True,
                body="Welcome! Here's 10% off your first order — just mention this message at checkout.",
            ),
            Promotion(
                title="Clearance (inactive)", active=False,
                body="Clearance items up to 50% off while stock lasts.",
            ),
        ])

        # --- Appointments for Priya (fully warmed line, nice for the screenshot)
        if warm_conversations:
            for i, convo in enumerate(random.sample(warm_conversations, k=min(4, len(warm_conversations)))):
                line = next(l for l in lines if l.id == convo.line_id)
                db.add(Appointment(
                    agent_id=line.agent_id, contact_id=convo.contact_id,
                    title=random.choice(["Follow-up call", "Send updated quote", "Confirm order details", "Check in after delivery"]),
                    scheduled_at=utcnow() + timedelta(days=i - 1, hours=random.randint(1, 6)),
                    done=i == 0,
                ))

        # --- Product catalog ----------------------------------------------
        db.add_all([
            Product(name="Classic tee", price_cents=1900, stock=120),
            Product(name="Hoodie", price_cents=4500, stock=40),
            Product(name="Cap", price_cents=1500, stock=0),
            Product(name="Tote bag", price_cents=1200, stock=75),
        ])

        await db.commit()

    print("Seed complete. Demo accounts (all use password: demo1234):")
    print("  admin@demo.com       (admin)")
    print("  supervisor@demo.com  (supervisor)")
    print("  nicole@demo.com      (agent, Line A - just connected)")
    print("  marcus@demo.com      (agent, Line B - warming up)")
    print("  priya@demo.com       (agent, Line C - fully warmed up)")


if __name__ == "__main__":
    asyncio.run(main())
