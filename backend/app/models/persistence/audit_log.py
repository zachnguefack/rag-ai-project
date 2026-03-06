from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AuditLogRecord(BaseModel):
    event_id: str
    correlation_id: str
    user_id: str
    question: str
    authorized_document_ids_count: int = 0
    documents_retrieved: list[str] = Field(default_factory=list)
    chunks_used: list[str] = Field(default_factory=list)
    access_decision: str = "deny"
    strict_scope_blocked: bool = False
    answer_generated: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float
