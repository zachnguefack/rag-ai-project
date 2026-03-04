from datetime import UTC, datetime, timedelta

import jwt

from app.config.settings import get_settings


def create_access_token(payload: dict) -> str:
    settings = get_settings()
    data = payload.copy()
    data["exp"] = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
