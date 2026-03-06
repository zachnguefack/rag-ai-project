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
    department_id: str = Field(..., examples=["dept-finance"])
    name: str = Field(..., examples=["Finance"])
    description: str = Field(default="", examples=["Finance and accounting department"])


class DepartmentResponse(BaseModel):
    department_id: str
    name: str
    description: str


class UserDepartmentUpdateRequest(BaseModel):
    department_id: str = Field(..., examples=["dept-operations"])


class UserDepartmentResponse(BaseModel):
    user_id: str
    department_id: str


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
    authorized_document_ids: list[str] = Field(default_factory=list)
