from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    event_id: str
    correlation_id: str
    user_id: str
    question: str
    authorized_document_ids_count: int
    documents_retrieved: list[str]
    chunks_used: list[str]
    access_decision: str
    strict_scope_blocked: bool
    answer_generated: str
    timestamp: datetime
    confidence_score: float


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse] = Field(default_factory=list)
    count: int
