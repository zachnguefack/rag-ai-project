from __future__ import annotations

from fastapi import Depends, FastAPI

from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings, load_settings
from app.services.rag_service import RAGApplicationService


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title=runtime_settings.app_name, version=runtime_settings.app_version)

    service = RAGApplicationService(runtime_settings)

    def service_dependency() -> RAGApplicationService:
        return service

    def settings_dependency() -> BackendSettings:
        return runtime_settings

    app.dependency_overrides[RAGApplicationService] = service_dependency
    app.dependency_overrides[BackendSettings] = settings_dependency

    app.include_router(build_v1_router(), prefix='/api/v1', tags=['rag'])
    return app


app = create_app()
