"""SQLAlchemy models for the demo.

Trimmed down from a production multichannel WhatsApp CRM: the pieces kept
here are the ones that show real design decisions (the anti-ban warm-up
ramp, the cold/warm contact distinction, alerting instead of hard-blocking)
rather than CRUD boilerplate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


TS = DateTime(timezone=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # admin: sees and does everything. supervisor: sees all agents, no selling.
    # agent: owns a WhatsApp line and its conversations.
    role: Mapped[str] = mapped_column(Text, nullable=False, default="agent")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    line: Mapped["WhatsAppLine | None"] = relationship(back_populates="agent", uselist=False)


class WhatsAppLine(Base):
    """A WhatsApp number assigned to one agent.

    `warmup_started_at` is the centerpiece of the whole anti-ban design: see
    `app/services/rate_limiter.py`. It resets whenever the line has to be
    re-linked (the number was banned, logged out, or just created) — a line
    with six months of history and a line that reconnected ten minutes ago
    are not the same risk, even if they belong to the same agent.
    """

    __tablename__ = "whatsapp_lines"

    id: Mapped[uuid.UUID] = _uuid_pk()
    phone_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="connected")
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    # The daily/hourly/new-chat ceilings this line is allowed to *grow into*.
    # The number it actually obeys right now is min(these, warm-up tier) -
    # see RateLimiter.effective_limits().
    policy_daily: Mapped[int] = mapped_column(Integer, nullable=False, default=250)
    policy_hourly: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    policy_new_chats_daily: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    warmup_started_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    agent: Mapped["User | None"] = relationship(back_populates="line")


class Contact(Base):
    """A generic CRM snapshot alongside the chat, not a specific ERP's
    schema - the production project syncs this from a real CRM (Odoo, in
    that case); the shape here is deliberately vendor-neutral."""

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    crm_account: Mapped[str | None] = mapped_column(Text)
    lifetime_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_order_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Conversation(Base):
    """A thread between one contact and one WhatsApp line.

    `first_inbound_at` is what makes a contact "warm": once they have written
    in at least once, outreach to them is a reply, not a cold open - WhatsApp
    treats those very differently for ban risk. See
    `Conversation.is_warm` and `BroadcastService` in services/broadcasts.py.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    contact_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("contacts.id"))
    line_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("whatsapp_lines.id"))
    first_inbound_at: Mapped[datetime | None] = mapped_column(TS)
    last_message_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    contact: Mapped[Contact] = relationship()
    line: Mapped[WhatsAppLine] = relationship()

    @property
    def is_warm(self) -> bool:
        return self.first_inbound_at is not None


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # "inbound" | "outbound"
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id")
    )
    sent_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Alert(Base):
    """Supervisor-facing notices. Nothing here blocks an agent from working -
    see the design note in services/rate_limiter.py about why."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class CallLog(Base):
    """A logged call against a conversation's contact.

    This is the stand-in for a PBX/telephony integration (the production
    project logs real call duration from a cloud phone system). There's no
    real phone call here - clicking "Call" just logs one with a plausible
    random duration - but the shape (who called, how long, linked to which
    conversation) is the part worth showing.
    """

    __tablename__ = "call_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class BroadcastRun(Base):
    """One past broadcast send, kept so the Broadcasts page has a history to
    show, not just a compose box. `skipped_cold` is a snapshot - a plain
    count, not a live link to those conversations - since the point is
    showing what happened at send time, not a query that could drift."""

    __tablename__ = "broadcast_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_by_user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_cold_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    sent_by: Mapped["User"] = relationship()


class SupportTicket(Base):
    """A problem reported by an agent or supervisor, for an admin to triage.

    Deliberately simple: three states, four priorities, one optional note
    back from whoever resolves it. The production project this is distilled
    from also attaches a screenshot - left out here since it doesn't add to
    the part worth showing (the state machine and who-can-see-what), just
    file-upload plumbing.
    """

    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    state: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    admin_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    reported_by: Mapped["User"] = relationship()


class Appointment(Base):
    """A follow-up reminder tied to a contact - "Agenda". Deliberately not
    a general-purpose calendar: just a title, a time, and a done flag, since
    the thing worth showing is that it's linked back to the conversation it
    came from, not a calendar UI."""

    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    agent_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    contact_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("contacts.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    contact: Mapped[Contact] = relationship()


class Goal(Base):
    """A monthly target an admin sets for an agent - "Objetivos". One row
    per agent per month; progress is computed live against it from
    `messages`/`conversations`, not stored, so it's never stale."""

    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = _uuid_pk()
    agent_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    target_messages_month: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    target_conversations_month: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Promotion(Base):
    """A reusable broadcast template - "Promociones". Its body prefills the
    Broadcasts compose box; it doesn't send anything by itself."""

    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Product(Base):
    """A minimal catalog entry - "Productos". Exists so a promotion or a
    chat reply can reference real stock/price, not because this demo needs
    inventory management."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
