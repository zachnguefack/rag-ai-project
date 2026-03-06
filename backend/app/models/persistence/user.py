from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.security.policies import RoleName


class UserRecord(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    password_hash: str
    is_active: bool = True
    roles: list[RoleName] = Field(default_factory=list)
    document_allow_list: list[str] = Field(default_factory=list)
