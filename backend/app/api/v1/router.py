from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin, ai, appointments, auth, broadcasts, conversations, dashboard, goals,
    metrics, products, promotions, support,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(broadcasts.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(support.router)
api_router.include_router(metrics.router)
api_router.include_router(appointments.router)
api_router.include_router(goals.router)
api_router.include_router(promotions.router)
api_router.include_router(products.router)
api_router.include_router(ai.router)
