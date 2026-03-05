from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.config.settings import BackendSettings, load_settings
from app.services.rag_service import RAGApplicationService


_runtime_settings: BackendSettings | None = None
_runtime_service: RAGApplicationService | None = None


def get_settings() -> BackendSettings:
    global _runtime_settings
    if _runtime_settings is None:
        _runtime_settings = load_settings()
    return _runtime_settings


def get_rag_service(settings: BackendSettings = Depends(get_settings)) -> RAGApplicationService:
    global _runtime_service
    if _runtime_service is None:
        _runtime_service = RAGApplicationService(settings)
    return _runtime_service


def validate_api_key(x_api_key: str | None = Header(default=None), settings: BackendSettings = Depends(get_settings)) -> None:
    if settings.allow_unauthenticated:
        return
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API key is not configured.",
        )
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")
