from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from app.config.settings import BackendSettings, load_settings
from app.models.domain.user import User
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService


_runtime_settings: BackendSettings | None = None
_runtime_service: RAGApplicationService | None = None
_runtime_rbac: RBACService | None = None


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


def get_rbac_service() -> RBACService:
    global _runtime_rbac
    if _runtime_rbac is None:
        _runtime_rbac = RBACService()
    return _runtime_rbac


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


def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> User:
    existing_user = getattr(request.state, "current_user", None)
    if existing_user is not None:
        return existing_user
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-Id header.")
    user = rbac_service.resolve_user(x_user_id)
    request.state.current_user = user
    return user
