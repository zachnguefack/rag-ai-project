from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    user_id: str
    question: str
    documents_retrieved: tuple[str, ...]
    answer_generated: str
    timestamp: datetime
    confidence_score: float
