from __future__ import annotations

from fastapi import HTTPException, status

from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.models.persistence.user import UserRecord
from app.security.password import hash_password, verify_password
from app.security.policies import RoleName


class UserService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        department_repository: DepartmentRepository | None = None,
        user_department_access_repository: UserDepartmentAccessRepository | None = None,
    ) -> None:
        self._users = user_repository or UserRepository()
        self._departments = department_repository or DepartmentRepository()
        self._department_access = user_department_access_repository or UserDepartmentAccessRepository()

    def list_users(self) -> list[UserRecord]:
        return self._users.list()

    def get_user(self, user_id: str) -> UserRecord:
        record = self._users.get(user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return record

    def create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        roles: list[RoleName],
        department_ids: list[str],
        is_active: bool,
        actor_user_id: str,
    ) -> UserRecord:
        if self._users.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
        if self._users.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

        normalized_roles = roles or [RoleName.STANDARD_USER]
        normalized_department_ids = list(dict.fromkeys(dep for dep in department_ids if dep))
        for department_id in normalized_department_ids:
            if self._departments.get(department_id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department not found: {department_id}")

        record = self._users.create(
            username=username,
            email=email,
            password_hash=hash_password(password),
            roles=normalized_roles,
            department_id=normalized_department_ids[0] if normalized_department_ids else "",
        )
        if not is_active:
            updated = self._users.set_active(record.user_id, False)
            if updated is not None:
                record = updated

        for department_id in normalized_department_ids:
            self._department_access.assign(
                user_id=record.user_id,
                department_id=department_id,
                assigned_by=actor_user_id,
            )

        return self.get_user(record.user_id)

    def update_user(
        self,
        user_id: str,
        *,
        username: str | None,
        email: str | None,
        is_active: bool | None,
    ) -> UserRecord:
        existing = self.get_user(user_id)

        if username is not None and username != existing.username:
            by_username = self._users.get_by_username(username)
            if by_username is not None and by_username.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

        if email is not None and str(email) != str(existing.email):
            by_email = self._users.get_by_email(str(email))
            if by_email is not None and by_email.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

        updated = self._users.update_profile(user_id, username=username, email=str(email) if email else None, is_active=is_active)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return updated

    def set_active(self, user_id: str, is_active: bool) -> UserRecord:
        updated = self._users.set_active(user_id, is_active)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return updated

    def reset_password(self, user_id: str, new_password: str) -> None:
        self.get_user(user_id)
        updated = self._users.set_password_hash(user_id, hash_password(new_password))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    def change_own_password(self, user_id: str, current_password: str, new_password: str) -> None:
        record = self.get_user(user_id)
        if not verify_password(current_password, record.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is invalid.")
        updated = self._users.set_password_hash(user_id, hash_password(new_password))
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
