"""Agenda: follow-up reminders tied to a contact."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import CurrentUser, DbSession
from app.db.models import Appointment
from app.schemas import AppointmentIn, AppointmentOut

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(user: CurrentUser, db: DbSession) -> list[AppointmentOut]:
    stmt = (
        select(Appointment)
        .options(joinedload(Appointment.contact))
        .where(Appointment.agent_id == user.id)
        .order_by(Appointment.done, Appointment.scheduled_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [AppointmentOut.model_validate(a) for a in rows]


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(payload: AppointmentIn, user: CurrentUser, db: DbSession) -> AppointmentOut:
    appt = Appointment(
        agent_id=user.id, contact_id=payload.contact_id, title=payload.title,
        scheduled_at=payload.scheduled_at,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt, attribute_names=["contact"])
    return AppointmentOut.model_validate(appt)


@router.post("/{appointment_id}/done", response_model=AppointmentOut)
async def mark_done(appointment_id: uuid.UUID, user: CurrentUser, db: DbSession) -> AppointmentOut:
    appt = await db.get(Appointment, appointment_id)
    if not appt or appt.agent_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    appt.done = True
    await db.commit()
    await db.refresh(appt, attribute_names=["contact"])
    return AppointmentOut.model_validate(appt)
