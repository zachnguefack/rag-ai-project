from __future__ import annotations

import threading
from datetime import datetime

from app.models.persistence.audit_log import AuditLogRecord


class AuditLogRepository:
    """In-memory audit log repository."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[AuditLogRecord] = []

    def append(self, record: AuditLogRecord) -> AuditLogRecord:
        with self._lock:
            self._events.append(record)
        return record

    def list(
        self,
        *,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogRecord]:
        with self._lock:
            records = list(self._events)

        if user_id is not None:
            records = [record for record in records if record.user_id == user_id]
        if start_time is not None:
            records = [record for record in records if record.timestamp >= start_time]
        if end_time is not None:
            records = [record for record in records if record.timestamp <= end_time]

        records.sort(key=lambda record: record.timestamp, reverse=True)
        return records[offset : offset + limit]

    def get(self, event_id: str) -> AuditLogRecord | None:
        with self._lock:
            return next((event for event in self._events if event.event_id == event_id), None)
