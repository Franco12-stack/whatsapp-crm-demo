"""Promociones: reusable broadcast templates. Anyone can read them (an
agent picks one to prefill a broadcast); only admins create/edit them."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.db.models import Promotion
from app.schemas import PromotionIn, PromotionOut

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("", response_model=list[PromotionOut])
async def list_promotions(_: CurrentUser, db: DbSession) -> list[PromotionOut]:
    rows = (await db.execute(select(Promotion).order_by(Promotion.created_at.desc()))).scalars().all()
    return [PromotionOut.model_validate(p) for p in rows]


@router.post("", response_model=PromotionOut, status_code=status.HTTP_201_CREATED)
async def create_promotion(payload: PromotionIn, _: AdminUser, db: DbSession) -> PromotionOut:
    promo = Promotion(title=payload.title, body=payload.body, active=payload.active)
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return PromotionOut.model_validate(promo)


@router.patch("/{promotion_id}", response_model=PromotionOut)
async def update_promotion(
    promotion_id: uuid.UUID, payload: PromotionIn, _: AdminUser, db: DbSession
) -> PromotionOut:
    promo = await db.get(Promotion, promotion_id)
    if not promo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Promotion not found")
    promo.title, promo.body, promo.active = payload.title, payload.body, payload.active
    await db.commit()
    await db.refresh(promo)
    return PromotionOut.model_validate(promo)
