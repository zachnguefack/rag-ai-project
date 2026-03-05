from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AuditLogRecord(BaseModel):
    event_id: str
    user_id: str
    question: str
    documents_retrieved: list[str] = Field(default_factory=list)
    answer_generated: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float
