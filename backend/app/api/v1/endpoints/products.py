"""Productos: a minimal catalog. Same read-all/admin-writes shape as
promotions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.db.models import Product
from app.schemas import ProductIn, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(_: CurrentUser, db: DbSession) -> list[ProductOut]:
    rows = (await db.execute(select(Product).order_by(Product.name))).scalars().all()
    return [ProductOut.model_validate(p) for p in rows]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductIn, _: AdminUser, db: DbSession) -> ProductOut:
    product = Product(name=payload.name, price_cents=payload.price_cents, stock=payload.stock)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: uuid.UUID, payload: ProductIn, _: AdminUser, db: DbSession) -> ProductOut:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.name, product.price_cents, product.stock = payload.name, payload.price_cents, payload.stock
    await db.commit()
    await db.refresh(product)
    return ProductOut.model_validate(product)
