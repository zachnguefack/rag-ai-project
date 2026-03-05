from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.security.policies import RoleName


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["jane.doe"])
    email: EmailStr = Field(..., examples=["jane.doe@company.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Str0ngPassw0rd!"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["jane.doe"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Str0ngPassw0rd!"])


class AuthTokenResponse(BaseModel):
    access_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_at: datetime


class LogoutResponse(BaseModel):
    message: str = Field(default="Logged out successfully", examples=["Logged out successfully"])


class MeResponse(BaseModel):
    user_id: str = Field(..., examples=["f7e86566-6902-4b55-a1cf-2145f5fb7cc6"])
    username: str = Field(..., examples=["jane.doe"])
    email: EmailStr = Field(..., examples=["jane.doe@company.com"])
    is_active: bool = Field(..., examples=[True])
    roles: list[RoleName]


class UserPermissionsResponse(BaseModel):
    permissions: list[str]
    roles: list[str]
