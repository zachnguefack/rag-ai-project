from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, EmailStr, Field

from app.security.policies import RoleName


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class MeResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    is_active: bool
    roles: list[RoleName]
