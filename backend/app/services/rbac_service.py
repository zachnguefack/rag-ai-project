from __future__ import annotations

from fastapi import HTTPException, status

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.role_repo import RoleRepository
from app.database.repositories.user_repo import UserRepository
from app.models.domain.role import Role
from app.models.domain.user import User
from app.models.persistence.permission import PermissionCheckResult
from app.models.schema.admin import RBACValidateResponse
from app.security.policies import Permission, RoleName


from app.services.document_access_service import DocumentAccessService


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
        self._document_access = DocumentAccessService(document_repository=self._documents)

    def resolve_user(self, user_id: str) -> User:
        record = self._users.get(user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user identity.")

        roles = tuple(self._roles.get(role_name) for role_name in record.roles)
        user = self._users.hydrate(record, roles)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")
        return user

    def list_roles(self) -> tuple[Role, ...]:
        return self._roles.list()

    def get_role(self, role_name: RoleName) -> Role:
        return self._roles.get(role_name)

    def get_user_roles(self, user_id: str) -> list[RoleName]:
        record = self._users.get(user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return list(record.roles)

    def replace_user_roles(self, user_id: str, roles: list[RoleName]) -> list[RoleName]:
        record = self._users.set_roles(user_id=user_id, roles=roles)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return list(record.roles)

    def validate_permission(self, user: User, permission: Permission) -> PermissionCheckResult:
        granted = permission in user.permissions
        reason = "Role grants permission." if granted else "No assigned role grants this permission."
        return PermissionCheckResult(granted=granted, permission=permission, reason=reason)

    def enforce_permission(self, user: User, permission: Permission) -> None:
        result = self.validate_permission(user, permission)
        if not result.granted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.reason)

    def validate_access(self, user_id: str, permission: Permission, document_id: str | None = None) -> RBACValidateResponse:
        user = self.resolve_user(user_id)
        permission_result = self.validate_permission(user, permission)
        if not permission_result.granted:
            return RBACValidateResponse(
                user_id=user_id,
                permission=permission,
                document_id=document_id,
                allowed=False,
                reason=permission_result.reason,
            )

        if document_id is not None:
            try:
                self.enforce_document_access(user, document_id)
            except HTTPException as exc:
                return RBACValidateResponse(
                    user_id=user_id,
                    permission=permission,
                    document_id=document_id,
                    allowed=False,
                    reason=str(exc.detail),
                )

        role_names = ",".join(sorted(role.value for role in user.role_names))
        return RBACValidateResponse(
            user_id=user_id,
            permission=permission,
            document_id=document_id,
            allowed=True,
            reason=f"role={role_names}",
        )

    def verify_roles(self, user: User, allowed_roles: set[RoleName]) -> None:
        if not (user.role_names & allowed_roles):
            readable = ", ".join(sorted(role.value for role in allowed_roles))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"One of [{readable}] roles is required.")

    def enforce_document_access(self, user: User, document_id: str) -> None:
        self.enforce_permission(user, Permission.READ_DOCUMENT)
        document = self._documents.get(document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")

        decision = self._document_access.can_access_document(user=user, document=document)
        if not decision.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: {decision.reason}")
