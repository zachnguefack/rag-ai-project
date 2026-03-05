from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings, load_settings
from app.security.middleware import RBACMiddleware
from app.services.auth_service import AuthService
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title=runtime_settings.app_name, version=runtime_settings.app_version)

    service = RAGApplicationService(runtime_settings)
    rbac_service = RBACService()
    auth_service = AuthService(settings=runtime_settings)

    def service_dependency() -> RAGApplicationService:
        return service

    def settings_dependency() -> BackendSettings:
        return runtime_settings

    def rbac_dependency() -> RBACService:
        return rbac_service

    def auth_dependency() -> AuthService:
        return auth_service

    app.dependency_overrides[RAGApplicationService] = service_dependency
    app.dependency_overrides[BackendSettings] = settings_dependency
    app.dependency_overrides[RBACService] = rbac_dependency
    app.dependency_overrides[AuthService] = auth_dependency

    app.add_middleware(RBACMiddleware, rbac_service=rbac_service, auth_service=auth_service)
    app.include_router(build_v1_router(), prefix='/api/v1', tags=['rag'])
    return app


app = create_app()
