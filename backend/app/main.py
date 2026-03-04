from fastapi import FastAPI

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.observability.logging import configure_logging
from app.security.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router, prefix="/v1")
    return app


app = create_app()
