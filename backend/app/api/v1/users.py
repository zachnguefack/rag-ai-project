from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_rbac_service, get_user_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.admin import ChangeOwnPasswordRequest, PasswordChangeResponse
from app.models.schema.auth import MeResponse, UserPermissionsResponse
from app.models.schema.common import ErrorResponse
from app.security.policies import Permission
from app.services.rbac_service import RBACService
from app.services.user_service import UserService

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
        department_ids=list(current_user.effective_department_ids),
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


@router.post(
    '/change-password',
    response_model=PasswordChangeResponse,
    summary="Change own password",
    description="Allows an authenticated user to change their own password by providing current and new password.",
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def change_own_password(
    payload: ChangeOwnPasswordRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> PasswordChangeResponse:
    user_service.change_own_password(
        user_id=current_user.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return PasswordChangeResponse()
