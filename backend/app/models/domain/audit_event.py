from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    correlation_id: str
    user_id: str
    question: str
    authorized_document_ids_count: int
    documents_retrieved: tuple[str, ...]
    chunks_used: tuple[str, ...]
    access_decision: str
    strict_scope_blocked: bool
    answer_generated: str
    timestamp: datetime
    confidence_score: float
