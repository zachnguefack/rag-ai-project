from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.auth import MeResponse, UserPermissionsResponse
from app.models.schema.common import ErrorResponse
from app.security.policies import Permission
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    '/me',
    response_model=MeResponse,
    summary="Get authenticated user",
    description="Returns the authenticated user context used for authorization decisions.",
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid token/API key."}},
    dependencies=[Depends(validate_api_key)],
)
def get_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        department_id=current_user.department_id,
        roles=sorted(current_user.role_names, key=lambda role: role.value),
    )


@router.get(
    '/permissions',
    response_model=UserPermissionsResponse,
    summary="List effective permissions",
    description="Returns the effective permissions and roles for the current user.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def my_permissions(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> UserPermissionsResponse:
    rbac_service.enforce_permission(current_user, Permission.READ_DOCUMENT)
    return UserPermissionsResponse(
        permissions=sorted(permission.value for permission in current_user.permissions),
        roles=sorted(role.value for role in current_user.role_names),
    )
