from app.config.settings import get_settings


class ConfigService:
    def get_runtime_config(self) -> dict:
        settings = get_settings()
        return {"app_name": settings.app_name, "environment": settings.environment}
