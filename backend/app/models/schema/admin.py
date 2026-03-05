from __future__ import annotations

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
    document_id: str | None = Field(default=None, examples=["doc-public"])


class RBACValidateResponse(BaseModel):
    user_id: str
    permission: Permission
    document_id: str | None = None
    allowed: bool
    reason: str
