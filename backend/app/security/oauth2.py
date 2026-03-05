from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="JWT access token obtained from the `/api/v1/auth/login` endpoint.",
    auto_error=False,
)


def extract_bearer_token(credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme.")
    return credentials.credentials
