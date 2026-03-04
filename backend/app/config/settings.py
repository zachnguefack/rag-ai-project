from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", extra="ignore")

    app_name: str = "Enterprise RAG Backend"
    app_version: str = "1.0.0"
    environment: str = "dev"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./rag_backend.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
