from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    email: str
    role: str


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    phone_number: str
    crm_account: str | None = None
    lifetime_value: int = 0
    last_order_at: datetime | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    direction: str
    body: str
    sent_by_user_id: uuid.UUID | None
    sent_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contact: ContactOut
    line_id: uuid.UUID
    is_warm: bool
    last_message_at: datetime


class SendMessageIn(BaseModel):
    body: str


class ReassignIn(BaseModel):
    line_id: uuid.UUID


class BroadcastIn(BaseModel):
    conversation_ids: list[uuid.UUID]
    body: str
    force: bool = False


class BroadcastOut(BaseModel):
    sent_to: list[uuid.UUID]
    skipped_cold: list[dict]


class BroadcastRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    body: str
    sent_by: UserOut
    sent_count: int
    skipped_cold_count: int
    forced: bool
    created_at: datetime


class CallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    duration_seconds: int
    created_at: datetime


class SupportTicketIn(BaseModel):
    title: str
    description: str
    priority: str = "medium"


class SupportTicketUpdateIn(BaseModel):
    state: str
    admin_note: str | None = None


class SupportTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str
    priority: str
    state: str
    reported_by: UserOut
    admin_note: str | None
    created_at: datetime
    updated_at: datetime


class MetricsOut(BaseModel):
    messages_today: int
    messages_this_week: int
    messages_this_month: int
    conversations_total: int
    conversations_warm: int
    conversations_cold: int
    calls_logged: int
    broadcasts_sent: int
    tickets_open: int


class LineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone_number: str
    label: str
    status: str
    agent_id: uuid.UUID | None
    policy_daily: int
    policy_hourly: int
    policy_new_chats_daily: int
    warmup_started_at: datetime
    usage_percent: float = 0.0
    effective_daily_limit: int = 0
    days_connected: int = 0


class LinePolicyIn(BaseModel):
    policy_daily: int
    policy_hourly: int
    policy_new_chats_daily: int


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    title: str
    detail: str | None
    acknowledged: bool
    created_at: datetime


class AgentStatusOut(BaseModel):
    user: UserOut
    line: LineOut | None
    open_conversations: int
    messages_today: int


class AppointmentIn(BaseModel):
    contact_id: uuid.UUID
    title: str
    scheduled_at: datetime


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    contact: ContactOut
    title: str
    scheduled_at: datetime
    done: bool


class GoalIn(BaseModel):
    target_messages_month: int
    target_conversations_month: int


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    agent_id: uuid.UUID
    target_messages_month: int
    target_conversations_month: int
    progress_messages: int = 0
    progress_conversations: int = 0


class PromotionIn(BaseModel):
    title: str
    body: str
    active: bool = True


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    active: bool


class ProductIn(BaseModel):
    name: str
    price_cents: int
    stock: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    price_cents: int
    stock: int


class AiSuggestIn(BaseModel):
    conversation_id: uuid.UUID


class AiSuggestOut(BaseModel):
    suggestion: str
    note: str = "Demo mode: canned suggestion, not a live model call."
