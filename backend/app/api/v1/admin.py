from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_current_user, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.audit import AuditLogListResponse, AuditLogResponse
from app.models.schema.common import ErrorResponse
from app.security.policies import Permission
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService

router = APIRouter(tags=["Admin", "Audit"])


@router.get(
    '/admin/audit-logs',
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="Returns paginated audit query events with optional time/user filters.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
)
def list_audit_logs(
    user_id: str | None = Query(default=None, description="Filter logs by user ID."),
    start_time: datetime | None = Query(default=None, description="Include logs from this timestamp."),
    end_time: datetime | None = Query(default=None, description="Include logs up to this timestamp."),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of records to return."),
    offset: int = Query(default=0, ge=0, description="Offset for pagination."),
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


@router.get(
    '/admin/audit-logs/{event_id}',
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description="Returns details for a single audit event.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
)
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
