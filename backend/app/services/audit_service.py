from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.database.repositories.audit_repo import AuditLogRepository
from app.models.domain.audit_event import AuditEvent
from app.models.persistence.audit_log import AuditLogRecord


class AuditService:
    def __init__(self, repository: AuditLogRepository | None = None) -> None:
        self._repository = repository or AuditLogRepository()

    def record_query_event(
        self,
        *,
        user_id: str,
        question: str,
        documents_retrieved: list[str],
        answer_generated: str,
        confidence_score: float,
    ) -> AuditEvent:
        record = AuditLogRecord(
            event_id=str(uuid4()),
            user_id=user_id,
            question=question,
            documents_retrieved=documents_retrieved,
            answer_generated=answer_generated,
            confidence_score=confidence_score,
        )
        saved = self._repository.append(record)
        return self._to_domain(saved)

    def list_events(
        self,
        *,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        events = self._repository.list(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return [self._to_domain(event) for event in events]

    def get_event(self, event_id: str) -> AuditEvent | None:
        event = self._repository.get(event_id)
        if event is None:
            return None
        return self._to_domain(event)

    def _to_domain(self, record: AuditLogRecord) -> AuditEvent:
        return AuditEvent(
            event_id=record.event_id,
            user_id=record.user_id,
            question=record.question,
            documents_retrieved=tuple(record.documents_retrieved),
            answer_generated=record.answer_generated,
            timestamp=record.timestamp,
            confidence_score=record.confidence_score,
        )
