from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_audit_service, get_current_user, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.admin import (
    PermissionListResponse,
    RBACMatrixEntry,
    RBACMatrixResponse,
    RBACValidateRequest,
    RBACValidateResponse,
    RoleListResponse,
    RolePermissionsUpdateRequest,
    RoleSummaryResponse,
    UserRoleListResponse,
    UserRoleReplaceRequest,
)
from app.models.schema.audit import AuditLogListResponse, AuditLogResponse
from app.models.schema.common import ErrorResponse
from app.security.policies import Permission, RoleName
from app.security.rbac import require_permissions
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    '/audit-logs',
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="Returns paginated audit query events with optional time/user filters.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    tags=["Audit"],
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
    '/audit-logs/{event_id}',
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description="Returns details for a single audit event.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    tags=["Audit"],
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


@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List RBAC roles",
    description="Returns all roles with effective permissions from `app/security/policies.py`.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def list_roles(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> RoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = sorted(rbac_service.list_roles(), key=lambda role: role.name.value)
    return RoleListResponse(
        roles=[
            RoleSummaryResponse(
                role=role.name,
                permissions=sorted(role.permissions, key=lambda permission: permission.value),
            )
            for role in roles
        ]
    )


@router.get(
    "/roles/{role}",
    response_model=RoleSummaryResponse,
    summary="Get role details",
    description="Returns a single role and its permission set.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def get_role(
    role: RoleName,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> RoleSummaryResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    role_detail = rbac_service.get_role(role)
    return RoleSummaryResponse(
        role=role_detail.name,
        permissions=sorted(role_detail.permissions, key=lambda permission: permission.value),
    )


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    summary="List RBAC permissions",
    description="Returns all known permission claims from RBAC policy source of truth.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def list_permissions(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> PermissionListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return PermissionListResponse(permissions=sorted(Permission, key=lambda permission: permission.value))


@router.get(
    "/users/{user_id}/roles",
    response_model=UserRoleListResponse,
    summary="List user roles",
    description="Returns the roles currently assigned to a user.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def get_user_roles(
    user_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> UserRoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = rbac_service.get_user_roles(user_id)
    return UserRoleListResponse(user_id=user_id, roles=sorted(roles, key=lambda role_name: role_name.value))


@router.put(
    "/users/{user_id}/roles",
    response_model=UserRoleListResponse,
    summary="Replace user roles",
    description="Replaces the full role assignment set for a user.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def replace_user_roles(
    user_id: str,
    payload: UserRoleReplaceRequest,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> UserRoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = rbac_service.replace_user_roles(user_id=user_id, roles=payload.roles)
    return UserRoleListResponse(user_id=user_id, roles=sorted(roles, key=lambda role_name: role_name.value))


@router.put(
    "/roles/{role}/permissions",
    response_model=ErrorResponse,
    summary="Update role permissions",
    description="Role permission updates are immutable in this architecture and managed in policy source.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def replace_role_permissions(
    role: RoleName,
    payload: RolePermissionsUpdateRequest,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ErrorResponse:
    _ = (role, payload)
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Role permissions are defined in app/security/policies.py and cannot be modified via API.",
    )


@router.get(
    "/rbac/matrix",
    response_model=RBACMatrixResponse,
    summary="Get RBAC matrix",
    description="Returns the full role-to-permission mapping from `app/security/policies.py`.",
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def get_rbac_matrix(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> RBACMatrixResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return RBACMatrixResponse(
        matrix=[
            RBACMatrixEntry(
                role=role.name,
                permissions=sorted(role.permissions, key=lambda permission: permission.value),
            )
            for role in sorted(rbac_service.list_roles(), key=lambda role: role.name.value)
        ]
    )


@router.post(
    "/rbac/validate",
    response_model=RBACValidateResponse,
    summary="Validate RBAC access",
    description=(
        "Evaluates whether a user has a permission and optionally verifies document-level access using "
        "deny-by-default document checks."
    ),
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Roles & Permissions"],
)
@require_permissions(Permission.MANAGE_ROLES)
def validate_rbac_access(
    payload: RBACValidateRequest,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> RBACValidateResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return rbac_service.validate_access(
        user_id=payload.user_id,
        permission=payload.permission,
        document_id=payload.document_id,
    )
