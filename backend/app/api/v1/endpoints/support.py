"""Support tickets: an agent (or supervisor) reports a problem, an admin
triages it. Three states, no drag-and-drop - buttons that move a ticket
forward are simpler to get right than drag targets, and this is a kanban
board in the sense of "three columns by state," not a full reordering UI.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.db.models import SupportTicket, utcnow
from app.schemas import SupportTicketIn, SupportTicketOut, SupportTicketUpdateIn

router = APIRouter(prefix="/support", tags=["support"])


@router.get("", response_model=list[SupportTicketOut])
async def list_tickets(user: CurrentUser, db: DbSession) -> list[SupportTicketOut]:
    stmt = select(SupportTicket).options(joinedload(SupportTicket.reported_by)).order_by(
        SupportTicket.created_at.desc()
    )
    if user.role == "agent":
        stmt = stmt.where(SupportTicket.reported_by_user_id == user.id)
    rows = (await db.execute(stmt)).scalars().all()
    return [SupportTicketOut.model_validate(t) for t in rows]


@router.post("", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: SupportTicketIn, user: CurrentUser, db: DbSession) -> SupportTicketOut:
    ticket = SupportTicket(
        title=payload.title, description=payload.description, priority=payload.priority,
        reported_by_user_id=user.id,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket, attribute_names=["reported_by"])
    return SupportTicketOut.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=SupportTicketOut)
async def update_ticket(
    ticket_id: uuid.UUID, payload: SupportTicketUpdateIn, _: AdminUser, db: DbSession
) -> SupportTicketOut:
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    ticket.state = payload.state
    if payload.admin_note is not None:
        ticket.admin_note = payload.admin_note
    ticket.updated_at = utcnow()
    await db.commit()
    await db.refresh(ticket, attribute_names=["reported_by"])
    return SupportTicketOut.model_validate(ticket)
