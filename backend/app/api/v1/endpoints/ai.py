"""Asistente IA: a reply suggestion for the selected conversation.

Honest about what it is: canned, keyword-matched suggestions, not a live
model call - same spirit as the simulated WhatsApp provider. The production
project calls a real LLM here; wiring that into a public demo would mean
shipping an API key or asking visitors to bring their own, neither of which
is worth it just to show "a text box that calls an LLM," which is the
least interesting part of that integration anyway. What's shown instead is
the actual integration point: given a conversation's last inbound message,
return a suggestion keyed to it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models import Message
from app.schemas import AiSuggestIn, AiSuggestOut

router = APIRouter(prefix="/ai", tags=["ai"])

_RULES: list[tuple[tuple[str, ...], str]] = [
    (("price", "pricing", "cost", "how much"), "Sure! Here's our current price list — want me to send it over?"),
    (("discount", "deal", "cheaper"), "We can do a discount on orders of 3 or more — how many are you thinking?"),
    (("stock", "available", "in stock"), "Let me check stock for you real quick and I'll confirm in a minute."),
    (("order", "track", "shipping", "delivery"), "Happy to check on that — could you share your order number?"),
    (("call", "phone", "talk"), "Of course, I can call you — what time works best today?"),
    (("thanks", "thank you", "perfect", "great"), "Glad to help! Let me know if anything else comes up."),
]
_DEFAULT = "Thanks for reaching out! Could you tell me a bit more about what you're looking for?"


@router.post("/suggest", response_model=AiSuggestOut)
async def suggest_reply(payload: AiSuggestIn, _: CurrentUser, db: DbSession) -> AiSuggestOut:
    last_inbound = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == payload.conversation_id, Message.direction == "inbound")
            .order_by(Message.sent_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not last_inbound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No inbound message to reply to yet")

    text = last_inbound.body.lower()
    suggestion = next((reply for keywords, reply in _RULES if any(k in text for k in keywords)), _DEFAULT)
    return AiSuggestOut(suggestion=suggestion)
