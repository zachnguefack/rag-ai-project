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
    version_id: str = ""
    version: int
    content: str
    metadata: DocumentMetadata
    storage_path: str = ""
    checksum: str = ""
    indexed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentRecord(BaseModel):
    id: int | None = None
    document_id: str
    title: str
    department_id: str
    document_type: str = "policy"
    owner: str
    classification: str = "internal"
    status: str = "active"
    original_filename: str = ""
    stored_filename: str = ""
    storage_path: str = ""
    content_type: str = ""
    size_bytes: int = 0
    checksum: str = ""
    indexing_status: str = "pending"
    last_indexed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    versions: list[DocumentVersionRecord] = Field(default_factory=list)

    @property
    def current_version(self) -> int:
        if not self.versions:
            return 0
        return self.versions[-1].version
