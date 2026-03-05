from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.users import router as users_router


def build_v1_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(auth_router)
    router.include_router(users_router)
    router.include_router(documents_router)
    router.include_router(chat_router)
    router.include_router(retrieval_router)
    router.include_router(admin_router)
    return router
