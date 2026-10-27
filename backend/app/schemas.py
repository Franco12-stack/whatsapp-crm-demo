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


class BroadcastIn(BaseModel):
    conversation_ids: list[uuid.UUID]
    body: str
    force: bool = False


class BroadcastOut(BaseModel):
    sent_to: list[uuid.UUID]
    skipped_cold: list[dict]


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
