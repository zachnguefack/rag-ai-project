from __future__ import annotations

from datetime import datetime

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.deps import (
    get_audit_service,
    get_current_user,
    get_department_ingestion_service,
    get_department_service,
    get_document_access_service,
    get_user_department_access_repository,
    get_rbac_service,
    get_user_repository,
    validate_api_key,
)
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.models.domain.user import User
from app.models.schema.admin import (
    DepartmentCreateRequest,
    DepartmentDeleteResponse,
    DepartmentIngestFilePathRequest,
    DepartmentIngestFolderPathRequest,
    DepartmentFileListResponse,
    DepartmentIngestionResponse,
    DepartmentResponse,
    DepartmentUploadResultResponse,
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
    UserDepartmentAccessResponse,
    UserDocumentAccessResponse,
    UserDocumentScopeResponse,
    UserRoleListResponse,
    UserRoleReplaceRequest,
)
from app.models.schema.audit import AuditLogListResponse, AuditLogResponse
from app.models.schema.common import ErrorResponse
from app.models.schema.document import (
    AdminDocumentListResponse,
    DocumentAuditListResponse,
    DocumentDepartmentAssignmentRequest,
    DepartmentDocumentListItemResponse,
    DocumentMetadataDetailResponse,
    DocumentResponse,
)
from app.security.policies import Permission, RoleName
from app.security.rbac import require_permissions
from app.services.audit_service import AuditService
from app.services.department_service import DepartmentService
from app.services.department_ingestion_service import DepartmentIngestionService
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


@router.get('/departments', response_model=list[DepartmentResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"])
@require_permissions(Permission.MANAGE_USERS)
def list_departments(current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> list[DepartmentResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    return [DepartmentResponse(department_id=item.department_id, name=item.name, description=item.description, path=str(item.path), file_count=len(department_service.list_department_files(item.department_id))) for item in department_service.list_departments()]


@router.post('/departments', response_model=DepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"], summary="Create department with filesystem repository", description="Creates department and automatically creates /data/{department_name} repository folder.")
@require_permissions(Permission.MANAGE_USERS)
def create_department(payload: DepartmentCreateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    item = department_service.create_department(None, payload.name, payload.description, actor_user_id=current_user.user_id)
    return DepartmentResponse(department_id=item.department_id, name=item.name, description=item.description, path=str(item.path), file_count=0)


@router.get('/departments/{department_id}', response_model=DepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"])
@require_permissions(Permission.MANAGE_USERS)
def get_department(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    item = department_service.get_department(department_id)
    return DepartmentResponse(department_id=item.department_id, name=item.name, description=item.description, path=str(item.path), file_count=len(department_service.list_department_files(item.department_id)))


@router.get('/departments/{department_id}/documents', response_model=list[DepartmentDocumentListItemResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"])
@require_permissions(Permission.MANAGE_USERS)
def get_department_documents(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service), document_service: DocumentService = Depends(get_document_service)) -> list[DepartmentDocumentListItemResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    docs = department_service.list_documents_for_department(department_id)
    return [document_service.to_department_document_list_item(doc) for doc in docs]



@router.get('/departments/{department_id}/files', response_model=DepartmentFileListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"])
@require_permissions(Permission.MANAGE_USERS)
def list_department_files(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentFileListResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    department_service.get_department(department_id)
    return DepartmentFileListResponse(department_id=department_id, files=department_service.list_department_files(department_id))


@router.delete('/departments/{department_id}/files/{filename}', response_model=ErrorResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments"])
@require_permissions(Permission.MANAGE_USERS)
def delete_department_file(department_id: str, filename: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> ErrorResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    department_service.delete_file(department_id, filename)
    return ErrorResponse(detail="File deleted successfully.")

@router.delete('/departments/{department_id}', response_model=DepartmentDeleteResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Departments", "Admin"], summary="Delete department and purge repository", description="Destructive operation: deletes department documents, vector entries, physical files, and /data/{department_name} folder.")
@require_permissions(Permission.MANAGE_USERS)
def delete_department(department_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), department_service: DepartmentService = Depends(get_department_service)) -> DepartmentDeleteResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    payload = department_service.delete_department(department_id, actor_user_id=current_user.user_id)
    return DepartmentDeleteResponse(**payload)


@router.post(
    '/departments/{department_id}/upload',
    response_model=DepartmentUploadResultResponse,
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Department Ingestion", "Admin"],
    summary="Upload file(s) from client machine",
    description=(
        "Upload one or more files from the client machine using multipart/form-data. "
        "Swagger UI should render a file picker for the `files` field."
    ),
)
@require_permissions(Permission.MANAGE_USERS)
async def ingest_department_upload(
    department_id: str,
    files: List[UploadFile] = File(..., description="One or multiple files to ingest."),
    current_user: User = Depends(get_current_user),
    ingestion_service: DepartmentIngestionService = Depends(get_department_ingestion_service),
) -> DepartmentUploadResultResponse:
    return await ingestion_service.ingest_upload(user=current_user, department_id=department_id, files=files)


@router.post(
    '/departments/{department_id}/ingest-file-path',
    response_model=DepartmentIngestionResponse,
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Department Ingestion", "Admin"],
    summary="Ingest a single file already on server disk",
    description=(
        "Accepts JSON body `{\"file_path\": \"...\"}` for a file path that already exists on the server filesystem. "
        "The path must be within allowed ingest roots and must point to a supported file."
    ),
)
@require_permissions(Permission.MANAGE_USERS)
def ingest_department_file_path(
    department_id: str,
    payload: DepartmentIngestFilePathRequest,
    current_user: User = Depends(get_current_user),
    ingestion_service: DepartmentIngestionService = Depends(get_department_ingestion_service),
) -> DepartmentIngestionResponse:
    return ingestion_service.ingest_file_path(user=current_user, department_id=department_id, file_path=payload.file_path)


@router.post(
    '/departments/{department_id}/ingest-folder-path',
    response_model=DepartmentIngestionResponse,
    dependencies=[Depends(validate_api_key), Depends(get_current_user)],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    tags=["Department Ingestion", "Admin"],
    summary="Ingest all supported files from a folder on server disk",
    description=(
        "Accepts JSON body `{\"folder_path\": \"...\"}` for a folder that already exists on the server filesystem. "
        "All supported files found recursively in that folder are ingested."
    ),
)
@require_permissions(Permission.MANAGE_USERS)
def ingest_department_folder_path(
    department_id: str,
    payload: DepartmentIngestFolderPathRequest,
    current_user: User = Depends(get_current_user),
    ingestion_service: DepartmentIngestionService = Depends(get_department_ingestion_service),
) -> DepartmentIngestionResponse:
    return ingestion_service.ingest_folder_path(user=current_user, department_id=department_id, folder_path=payload.folder_path)


@router.put('/users/{user_id}/department', response_model=UserDepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def set_user_department(user_id: str, payload: UserDepartmentUpdateRequest, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service), user_repository: UserRepository = Depends(get_user_repository), department_service: DepartmentService = Depends(get_department_service)) -> UserDepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    department_service.get_department(payload.department_id)
    record = user_repository.set_department(user_id, payload.department_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    return UserDepartmentResponse(user_id=user_id, department_id=record.department_id)


@router.post('/users/{user_id}/departments/{department_id}', response_model=UserDepartmentAccessResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def assign_user_department(
    user_id: str,
    department_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    user_repository: UserRepository = Depends(get_user_repository),
    department_service: DepartmentService = Depends(get_department_service),
    user_department_access_repository: UserDepartmentAccessRepository = Depends(get_user_department_access_repository),
) -> UserDepartmentAccessResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    department = department_service.get_department(department_id)
    access = user_department_access_repository.assign(user_id=user_id, department_id=department.department_id, assigned_by=current_user.user_id)
    # Keep legacy primary department aligned with RBAC membership for backward compatibility.
    user_repository.set_department(user_id, department.department_id)
    return UserDepartmentAccessResponse(**access.model_dump())


@router.delete('/users/{user_id}/departments/{department_id}', response_model=UserDepartmentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def remove_user_department(
    user_id: str,
    department_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    user_repository: UserRepository = Depends(get_user_repository),
    department_service: DepartmentService = Depends(get_department_service),
    user_department_access_repository: UserDepartmentAccessRepository = Depends(get_user_department_access_repository),
) -> UserDepartmentResponse:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    department = department_service.get_department(department_id)
    removed = user_department_access_repository.remove(user_id=user_id, department_id=department.department_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User-department assignment not found.')
    return UserDepartmentResponse(user_id=user_id, department_id=department.department_id)


@router.get('/users/{user_id}/departments', response_model=list[UserDepartmentAccessResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def list_user_departments(
    user_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    user_repository: UserRepository = Depends(get_user_repository),
    user_department_access_repository: UserDepartmentAccessRepository = Depends(get_user_department_access_repository),
) -> list[UserDepartmentAccessResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    if user_repository.get(user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found.')
    return [UserDepartmentAccessResponse(**record.model_dump()) for record in user_department_access_repository.list_departments_for_user(user_id)]


@router.get('/departments/{department_id}/users', response_model=list[UserDepartmentAccessResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"])
@require_permissions(Permission.MANAGE_USERS)
def list_department_users(
    department_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    department_service: DepartmentService = Depends(get_department_service),
    user_department_access_repository: UserDepartmentAccessRepository = Depends(get_user_department_access_repository),
) -> list[UserDepartmentAccessResponse]:
    rbac_service.enforce_permission(current_user, Permission.MANAGE_USERS)
    department = department_service.get_department(department_id)
    return [UserDepartmentAccessResponse(**record.model_dump()) for record in user_department_access_repository.list_users_for_department(department.department_id)]


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
    return UserDocumentScopeResponse(user_id=user.user_id, department_id=user.department_id, department_ids=list(user.effective_department_ids), authorized_document_ids=scope)


@router.get('/documents', response_model=AdminDocumentListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"], summary="List all documents (admin)", description="Global document list for administrators. Not scope-limited.")
@require_permissions(Permission.MANAGE_USERS)
def admin_list_documents(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    department_id: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> AdminDocumentListResponse:
    return document_service.admin_list_documents(
        current_user,
        limit=limit,
        offset=offset,
        department_id=department_id,
        document_type=document_type,
        classification=classification,
        status_value=status,
        owner=owner,
    )


@router.get('/documents/{document_id}', response_model=DocumentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"], summary="Get document detail (admin)")
@require_permissions(Permission.MANAGE_USERS)
def admin_get_document(document_id: str, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    return document_service.admin_get_document(current_user, document_id)


@router.put('/documents/{document_id}/department', response_model=DocumentMetadataDetailResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"], summary="Reassign document department", description="Reassigns a document to a different owning department. document_id is an internal identifier.")
@require_permissions(Permission.MANAGE_USERS)
def admin_reassign_document_department(
    document_id: str,
    payload: DocumentDepartmentAssignmentRequest,
    current_user: User = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentMetadataDetailResponse:
    department_service.get_department(payload.department_id)
    return document_service.reassign_document_department(current_user, document_id, payload.department_id)


@router.get('/documents/{document_id}/audit', response_model=DocumentAuditListResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)], tags=["Admin"], summary="Get document audit history")
@require_permissions(Permission.READ_AUDIT_LOG)
def admin_get_document_audit(
    document_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentAuditListResponse:
    return document_service.admin_get_document_audit(current_user, document_id, limit=limit, offset=offset)
