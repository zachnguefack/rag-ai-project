from __future__ import annotations

from app.services.audit_service import AuditService


def export_audit_events(service: AuditService, *, user_id: str | None = None) -> list[dict]:
    return [event.__dict__ for event in service.list_events(user_id=user_id)]
