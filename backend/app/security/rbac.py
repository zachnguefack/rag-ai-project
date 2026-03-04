from fastapi import HTTPException, status

from app.services.rbac_service import RBACService


def require_permission(user: dict, permission: str) -> None:
    roles = user.get("roles", [])
    if not RBACService().has_permission(roles, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
