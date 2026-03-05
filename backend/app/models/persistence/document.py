from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    owner_user_id: str
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_users: list[str] = Field(default_factory=list)
    classification: str = "internal"
