from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class IngestJobRecord(BaseModel):
    job_id: str
    document_id: str | None = None
    status: str = "queued"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    indexed_files: int = 0
    indexed_chunks: int = 0
    removed_files: int = 0
    reused_existing_index: bool = False
    error_message: str | None = None
