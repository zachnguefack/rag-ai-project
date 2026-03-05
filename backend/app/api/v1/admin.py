from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_current_user, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.audit import AuditLogListResponse, AuditLogResponse
from app.security.policies import Permission
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService

router = APIRouter()


@router.get('/admin/audit-logs', response_model=AuditLogListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def list_audit_logs(
    user_id: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    rbac_service.enforce_permission(current_user, Permission.READ_AUDIT_LOG)
    items = audit_service.list_events(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    payload = [
        AuditLogResponse(
            event_id=item.event_id,
            user_id=item.user_id,
            question=item.question,
            documents_retrieved=list(item.documents_retrieved),
            answer_generated=item.answer_generated,
            timestamp=item.timestamp,
            confidence_score=item.confidence_score,
        )
        for item in items
    ]
    return AuditLogListResponse(items=payload, count=len(payload))


@router.get('/admin/audit-logs/{event_id}', response_model=AuditLogResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def get_audit_log(
    event_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditLogResponse:
    rbac_service.enforce_permission(current_user, Permission.READ_AUDIT_LOG)
    event = audit_service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Audit event not found.')

    return AuditLogResponse(
        event_id=event.event_id,
        user_id=event.user_id,
        question=event.question,
        documents_retrieved=list(event.documents_retrieved),
        answer_generated=event.answer_generated,
        timestamp=event.timestamp,
        confidence_score=event.confidence_score,
    )
