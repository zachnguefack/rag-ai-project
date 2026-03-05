from __future__ import annotations

from fastapi import HTTPException, status

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.role_repo import RoleRepository
from app.database.repositories.user_repo import UserRepository
from app.models.domain.user import User
from app.models.persistence.permission import PermissionCheckResult
from app.security.policies import DOCUMENT_GLOBAL_ACCESS_ROLES, Permission, RoleName


class RBACService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._roles = role_repository or RoleRepository()
        self._documents = document_repository or DocumentRepository()

    def resolve_user(self, user_id: str) -> User:
        record = self._users.get(user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user identity.")

        roles = tuple(self._roles.get(role_name) for role_name in record.roles)
        user = self._users.hydrate(record, roles)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")
        return user

    def validate_permission(self, user: User, permission: Permission) -> PermissionCheckResult:
        granted = permission in user.permissions
        reason = "Role grants permission." if granted else "No assigned role grants this permission."
        return PermissionCheckResult(granted=granted, permission=permission, reason=reason)

    def enforce_permission(self, user: User, permission: Permission) -> None:
        result = self.validate_permission(user, permission)
        if not result.granted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.reason)

    def verify_roles(self, user: User, allowed_roles: set[RoleName]) -> None:
        if not (user.role_names & allowed_roles):
            readable = ", ".join(sorted(role.value for role in allowed_roles))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"One of [{readable}] roles is required.")

    def enforce_document_access(self, user: User, document_id: str) -> None:
        self.enforce_permission(user, Permission.READ_DOCUMENT)
        document = self._documents.get(document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")

        if user.role_names & DOCUMENT_GLOBAL_ACCESS_ROLES:
            return

        if document.owner_user_id == user.user_id:
            return

        if user.user_id in document.allowed_users or document_id in user.document_allow_list:
            return

        allowed_roles = {RoleName(value) for value in document.allowed_roles}
        if allowed_roles & user.role_names:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user is not authorized for this document.",
        )
