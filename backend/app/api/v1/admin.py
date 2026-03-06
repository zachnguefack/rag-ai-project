from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_audit_service,
    get_current_user,
    get_department_service,
    get_document_access_service,
    get_rbac_service,
    get_user_repository,
    validate_api_key,
)
from app.database.repositories.user_repo import UserRepository
from app.models.domain.user import User
from app.models.schema.admin import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DocumentAccessGrantRequest,
    PermissionListResponse,
    RBACMatrixEntry,
    RBACMatrixResponse,
    RBACValidateRequest,
    RBACValidateResponse,
    RoleListResponse,
    RolePermissionsUpdateRequest,
    RoleSummaryResponse,
    UserDepartmentResponse,
    UserDepartmentUpdateRequest,
    UserDocumentAccessResponse,
    UserDocumentScopeResponse,
    UserRoleListResponse,
    UserRoleReplaceRequest,
)
from app.models.schema.audit import AuditLogListResponse, AuditLogResponse
from app.models.schema.common import ErrorResponse
from app.models.schema.document import DocumentResponse
from app.security.policies import Permission, RoleName
from app.security.rbac import require_permissions
from app.services.audit_service import AuditService
from app.services.department_service import DepartmentService
from app.services.document_access_service import DocumentAccessService
from app.api.deps import get_document_service
from app.services.document_service import DocumentService
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get('/audit-logs', response_model=AuditLogListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Audit"])
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
    items = audit_service.list_events(user_id=user_id, start_time=start_time, end_time=end_time, limit=limit, offset=offset)
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


@router.get('/audit-logs/{event_id}', response_model=AuditLogResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Audit"])
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


@router.get('/roles', response_model=RoleListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def list_roles(current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> RoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = sorted(rbac_service.list_roles(), key=lambda role: role.name.value)
    return RoleListResponse(roles=[RoleSummaryResponse(role=role.name, permissions=sorted(role.permissions, key=lambda p: p.value)) for role in roles])


@router.get('/roles/{role}', response_model=RoleSummaryResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def get_role(role: RoleName, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> RoleSummaryResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    role_detail = rbac_service.get_role(role)
    return RoleSummaryResponse(role=role_detail.name, permissions=sorted(role_detail.permissions, key=lambda p: p.value))


@router.get('/permissions', response_model=PermissionListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def list_permissions(current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> PermissionListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return PermissionListResponse(permissions=sorted(Permission, key=lambda p: p.value))


@router.get('/users/{user_id}/roles', response_model=UserRoleListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def get_user_roles(user_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> UserRoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = rbac_service.get_user_roles(user_id)
    return UserRoleListResponse(user_id=user_id, roles=sorted(roles, key=lambda role_name: role_name.value))


@router.put('/users/{user_id}/roles', response_model=UserRoleListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def replace_user_roles(user_id: str, payload: UserRoleReplaceRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> UserRoleListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    roles = rbac_service.replace_user_roles(user_id=user_id, roles=payload.roles)
    return UserRoleListResponse(user_id=user_id, roles=sorted(roles, key=lambda role_name: role_name.value))


@router.put('/roles/{role}/permissions', response_model=ErrorResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def replace_role_permissions(role: RoleName, payload: RolePermissionsUpdateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> ErrorResponse:
    _ = (role, payload)
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role permissions are defined in app/security/policies.py and cannot be modified via API.")


@router.get('/rbac/matrix', response_model=RBACMatrixResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def get_rbac_matrix(current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> RBACMatrixResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return RBACMatrixResponse(matrix=[RBACMatrixEntry(role=role.name, permissions=sorted(role.permissions, key=lambda p: p.value)) for role in sorted(rbac_service.list_roles(), key=lambda role: role.name.value)])


@router.post('/rbac/validate', response_model=RBACValidateResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Roles & Permissions"])
@require_permissions(Permission.MANAGE_ROLES)
def validate_rbac_access(payload: RBACValidateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> RBACValidateResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_ROLES)
    return rbac_service.validate_access(user_id=payload.user_id, permission=payload.permission, document_id=payload.document_id)


@router.get('/departments', response_model=list[DepartmentResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def list_departments(current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> list[DepartmentResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    return [DepartmentResponse(**item.model_dump()) for item in department_service.list_departments()]


@router.post('/departments', response_model=DepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def create_department(payload: DepartmentCreateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    item = department_service.create_department(payload.department_id, payload.name, payload.description)
    return DepartmentResponse(**item.model_dump())


@router.get('/departments/{department_id}', response_model=DepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def get_department(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    item = department_service.get_department(department_id)
    return DepartmentResponse(**item.model_dump())


@router.get('/departments/{department_id}/documents', response_model=list[DocumentResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def get_department_documents(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service), document_service: DocumentService = Depends(get_document_service)) -> list[DocumentResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    docs = department_service.list_documents_for_department(department_id)
    return [document_service._to_document_response(doc) for doc in docs]


@router.put('/users/{user_id}/department', response_model=UserDepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def set_user_department(user_id: str, payload: UserDepartmentUpdateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), department_service: DepartmentService = Depends(get_department_service)) -> UserDepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    department_service.get_department(payload.department_id)
    record = user_repository.set_department(user_id, payload.department_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    return UserDepartmentResponse(user_id=user_id, department_id=record.department_id)


@router.post('/users/{user_id}/document-access', response_model=UserDocumentAccessResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def grant_user_document_access(user_id: str, payload: DocumentAccessGrantRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), document_access_service: DocumentAccessService = Depends(get_document_access_service)) -> UserDocumentAccessResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    grant = document_access_service.grant_document_access(user_id=user_id, document_id=payload.document_id, granted_by=current_user.user_id)
    return UserDocumentAccessResponse(**grant.model_dump())


@router.get('/users/{user_id}/document-access', response_model=list[UserDocumentAccessResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def list_user_document_access(user_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), document_access_service: DocumentAccessService = Depends(get_document_access_service)) -> list[UserDocumentAccessResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    return [UserDocumentAccessResponse(**record.model_dump()) for record in document_access_service.list_document_access(user_id)]


@router.delete('/users/{user_id}/document-access/{document_id}', response_model=UserDocumentAccessResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def revoke_user_document_access(user_id: str, document_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), document_access_service: DocumentAccessService = Depends(get_document_access_service)) -> UserDocumentAccessResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    revoked = document_access_service.revoke_document_access(user_id=user_id, document_id=document_id)
    return UserDocumentAccessResponse(**revoked.model_dump())


@router.get('/users/{user_id}/document-scope', response_model=UserDocumentScopeResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def get_user_document_scope(user_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), document_access_service: DocumentAccessService = Depends(get_document_access_service)) -> UserDocumentScopeResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    record = user_repository.get(user_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    user = rbac_service.resolve_user(user_id)
    scope = document_access_service.compute_authorized_document_ids(user)
    return UserDocumentScopeResponse(user_id=user.user_id, department_id=user.department_id, authorized_document_ids=scope)
