from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    department: str
    owner: str
    classification: str
    status: str = "approved"
    permissions: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_user_ids: list[str] = Field(default_factory=list)
    allowed_departments: list[str] = Field(default_factory=list)


class DocumentVersionRecord(BaseModel):
    version_id: str
    document_id: str
    version_number: int
    content: str
    storage_path: str = ""
    checksum: str = ""
    indexed: bool = True
    approved_at: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: DocumentMetadata


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    document_type: str = "sop"
    owner_user_id: str
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_users: list[str] = Field(default_factory=list)
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_groups: list[str] = Field(default_factory=list)
    site_scope: str | None = None
    classification: str = "internal"
    status: str = "approved"
    department: str = "general"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    versions: list[DocumentVersionRecord] = Field(default_factory=list)

    @property
    def current_version(self) -> int:
        if not self.versions:
            return 0
        return self.versions[-1].version_number
