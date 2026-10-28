from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.simulator import run_customer_simulator

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.auto_seed:
        # Hosts like Render's free tier don't give you a shell to run
        # `python -m scripts.seed_demo` by hand, so the demo seeds itself on
        # first boot. seed_if_empty() is a no-op on every boot after that.
        from scripts.seed_demo import seed_if_empty

        try:
            await seed_if_empty()
        except Exception:  # noqa: BLE001 - never let a seeding hiccup block startup
            logger.exception("auto-seed failed")

    task = asyncio.create_task(run_customer_simulator())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="WhatsApp CRM Demo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
