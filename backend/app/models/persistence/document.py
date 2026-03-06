from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    department_id: str
    owner: str
    classification: str
    document_type: str = "policy"
    status: str = "active"


class DocumentVersionRecord(BaseModel):
    version: int
    content: str
    metadata: DocumentMetadata


class DocumentRecord(BaseModel):
    document_id: str
    title: str
    department_id: str
    document_type: str = "policy"
    owner: str
    classification: str = "internal"
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    versions: list[DocumentVersionRecord] = Field(default_factory=list)

    @property
    def current_version(self) -> int:
        if not self.versions:
            return 0
        return self.versions[-1].version
