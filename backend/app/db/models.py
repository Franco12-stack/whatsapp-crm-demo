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
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
