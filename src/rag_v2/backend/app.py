from __future__ import annotations

from fastapi import FastAPI

from .api import build_router
from .services import RAGApplicationService
from .settings import BackendSettings, load_settings


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(title=runtime_settings.app_name, version=runtime_settings.app_version)

    service = RAGApplicationService(runtime_settings)
    app.include_router(build_router(service=service, settings=runtime_settings), prefix="/api/v1", tags=["rag"])

    return app


app = create_app()
