from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, broadcasts, conversations, dashboard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(broadcasts.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
