from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_rbac_service
from app.models.domain.user import User
from app.models.schema.auth import MeResponse
from app.security.policies import Permission
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/users", tags=["users"])


@router.get('/me', response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=sorted(current_user.role_names, key=lambda role: role.value),
    )


@router.get('/permissions')
def my_permissions(
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> dict[str, list[str]]:
    rbac_service.enforce_permission(current_user, Permission.READ_DOCUMENT)
    return {
        "permissions": sorted(permission.value for permission in current_user.permissions),
        "roles": sorted(role.value for role in current_user.role_names),
    }
