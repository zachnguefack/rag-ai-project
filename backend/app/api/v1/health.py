from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.config.settings import BackendSettings
from app.models.schema.common import HealthResponse

router = APIRouter(tags=["System"])


@router.get('/health', response_model=HealthResponse, summary="Health check", description="Returns service status and version.")
def health(settings: BackendSettings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(service=settings.app_name, version=settings.app_version)
