from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    event_id: str
    user_id: str
    question: str
    documents_retrieved: list[str]
    answer_generated: str
    timestamp: datetime
    confidence_score: float


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse] = Field(default_factory=list)
    count: int
