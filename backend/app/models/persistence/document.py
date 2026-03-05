from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    department: str
    owner: str
    classification: str
    permissions: list[str] = Field(default_factory=list)


class DocumentVersionRecord(BaseModel):
    version: int
    content: str
    metadata: DocumentMetadata


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    owner_user_id: str
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_users: list[str] = Field(default_factory=list)
    classification: str = "internal"
    department: str = "general"
    versions: list[DocumentVersionRecord] = Field(default_factory=list)

    @property
    def current_version(self) -> int:
        if not self.versions:
            return 0
        return self.versions[-1].version
