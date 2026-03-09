from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.security.policies import Permission, RoleName


class RoleSummaryResponse(BaseModel):
    role: RoleName = Field(..., examples=[RoleName.STANDARD_USER])
    permissions: list[Permission] = Field(
        ..., examples=[[Permission.READ_DOCUMENT, Permission.SEARCH_DOCUMENT]]
    )


class RoleListResponse(BaseModel):
    roles: list[RoleSummaryResponse] = Field(default_factory=list)


class PermissionListResponse(BaseModel):
    permissions: list[Permission] = Field(default_factory=list)


class UserRoleListResponse(BaseModel):
    user_id: str = Field(..., examples=["u-standard"])
    roles: list[RoleName] = Field(default_factory=list)


class UserRoleReplaceRequest(BaseModel):
    roles: list[RoleName] = Field(..., examples=[[RoleName.STANDARD_USER, RoleName.POWER_USER]])


class RolePermissionsUpdateRequest(BaseModel):
    permissions: list[Permission] = Field(
        ..., examples=[[Permission.READ_DOCUMENT, Permission.SEARCH_DOCUMENT]]
    )


class RBACMatrixEntry(BaseModel):
    role: RoleName
    permissions: list[Permission] = Field(default_factory=list)


class RBACMatrixResponse(BaseModel):
    matrix: list[RBACMatrixEntry] = Field(default_factory=list)


class RBACValidateRequest(BaseModel):
    user_id: str = Field(..., examples=["u-power"])
    permission: Permission = Field(..., examples=[Permission.READ_DOCUMENT])
    document_id: str | None = Field(default=None, examples=["doc-eng"])


class RBACValidateResponse(BaseModel):
    user_id: str
    permission: Permission
    document_id: str | None = None
    allowed: bool
    reason: str


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., examples=["Finance"])
    description: str = Field(default="", examples=["Finance and accounting department"])


class DepartmentSummaryResponse(BaseModel):
    department_id: str
    name: str
    path: str
    file_count: int
    description: str = ""


class DepartmentDetailResponse(DepartmentSummaryResponse):
    files: list["DepartmentFileSummaryResponse"] = Field(default_factory=list)


class DepartmentResponse(DepartmentSummaryResponse):
    pass


class DepartmentFileSummaryResponse(BaseModel):
    name: str
    path: str
    size_bytes: int
    content_type: str | None = None
    last_modified: datetime


class DepartmentFileListResponse(BaseModel):
    department_id: str
    files: list[DepartmentFileSummaryResponse] = Field(default_factory=list)


class DepartmentUploadResultResponse(BaseModel):
    department_id: str
    ingested_documents: int
    indexed_files: int
    indexed_chunks: int
    storage_paths: list[str] = Field(default_factory=list)
    uploaded_files: list[DepartmentFileSummaryResponse] = Field(default_factory=list)


class UserDepartmentUpdateRequest(BaseModel):
    department_id: str = Field(..., examples=["dept-operations"])


class UserDepartmentResponse(BaseModel):
    user_id: str
    department_id: str


class UserDepartmentAccessResponse(BaseModel):
    user_id: str
    department_id: str
    assigned_by: str
    assigned_at: datetime


class DocumentAccessGrantRequest(BaseModel):
    document_id: str = Field(..., examples=["doc-eng"], description="Internal document identifier; not a filesystem path.")


class UserDocumentAccessResponse(BaseModel):
    id: str
    user_id: str
    document_id: str
    granted_by: str
    granted_at: datetime
    revoked_at: datetime | None
    is_active: bool


class UserDocumentScopeResponse(BaseModel):
    user_id: str
    department_id: str
    department_ids: list[str] = Field(default_factory=list)
    authorized_document_ids: list[str] = Field(default_factory=list)


class DepartmentDeleteResponse(BaseModel):
    department_id: str
    deleted_documents: int
    deleted_files: int
    deleted_repository: str


class DepartmentIngestFilePathRequest(BaseModel):
    file_path: str = Field(
        ...,
        min_length=1,
        examples=["/data/imports/report.pdf"],
        description="Absolute or server-local path to an existing file on server disk.",
    )


class DepartmentIngestFolderPathRequest(BaseModel):
    folder_path: str = Field(
        ...,
        min_length=1,
        examples=["/data/imports/monthly"],
        description="Absolute or server-local path to an existing folder on server disk.",
    )


class DepartmentIngestionResponse(BaseModel):
    department_id: str
    ingested_documents: int
    indexed_files: int
    indexed_chunks: int
    storage_paths: list[str] = Field(default_factory=list)
