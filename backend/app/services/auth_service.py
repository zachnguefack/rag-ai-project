"""Authentication service for JWT login and user identity hydration.

This module centralizes credential validation, token issuance/revocation, and
department-aware user hydration used by API dependencies and middleware.
"""

from __future__ import annotations

from datetime import datetime
import logging

from fastapi import HTTPException, status

from app.config.settings import BackendSettings
from app.database.repositories.role_repo import RoleRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.jwt import create_access_token, decode_access_token
from app.security.password import hash_password, verify_password
from app.security.policies import RoleName


LOGGER = logging.getLogger("app.auth")


class AuthService:
    """Handle registration, login, token lifecycle, and hydrated user resolution."""

    def __init__(
        self,
        settings: BackendSettings,
        user_repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
        user_department_access_repository: UserDepartmentAccessRepository | None = None,
    ) -> None:
        self._settings = settings
        self._users = user_repository or UserRepository()
        self._roles = role_repository or RoleRepository()
        self._department_access = user_department_access_repository or UserDepartmentAccessRepository()
        self._revoked_token_ids: set[str] = set()

    def register_user(self, username: str, email: str, password: str) -> UserRecord:
        if self._users.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
        if self._users.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

        password_hash = hash_password(password)
        return self._users.create(
            username=username,
            email=email,
            password_hash=password_hash,
            roles=[RoleName.STANDARD_USER],
        )

    def authenticate(self, username: str, password: str) -> UserRecord:
        record = self._users.get_by_username(username)
        if record is None or not verify_password(password, record.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
        if not record.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")
        return record


    def _resolve_department_membership(self, record: UserRecord) -> tuple[str, tuple[str, ...]]:
        """Resolve primary + effective departments from RBAC assignments with legacy fallback.

        Preference order:
        1. Explicit rows in ``user_department_access``.
        2. Legacy ``department_ids`` snapshot on the user record.
        3. Legacy single ``department_id`` field.
        """
        assigned_departments = [
            entry.department_id
            for entry in self._department_access.list_departments_for_user(record.user_id)
            if entry.department_id
        ]
        if assigned_departments:
            department_ids = tuple(sorted(set(assigned_departments)))
            if record.department_id and record.department_id not in department_ids:
                LOGGER.warning(
                    "Legacy user.department_id does not match RBAC assignments user_id=%s legacy=%s rbac=%s",
                    record.user_id,
                    record.department_id,
                    list(department_ids),
                )
            return department_ids[0], department_ids

        fallback_departments = [dep for dep in record.department_ids if dep]
        if fallback_departments:
            department_ids = tuple(dict.fromkeys(fallback_departments))
            return department_ids[0], department_ids

        if record.department_id:
            return record.department_id, (record.department_id,)

        return "", tuple()

    def hydrate_user(self, record: UserRecord) -> User:
        """Convert persistence model to runtime identity used in authorization checks."""
        roles = tuple(self._roles.get(role_name) for role_name in record.roles)
        primary_department_id, department_ids = self._resolve_department_membership(record)
        user = self._users.hydrate(record, roles)
        user.department_id = primary_department_id
        user.department_ids = department_ids
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")
        return user

    def issue_access_token(self, user: UserRecord) -> tuple[str, datetime]:
        """Issue an HMAC-signed short-lived access token for the authenticated user."""
        return create_access_token(
            subject=user.user_id,
            secret=self._settings.jwt_secret_key,
            expires_in_minutes=self._settings.jwt_access_token_expire_minutes,
        )

    def resolve_user_from_token(self, token: str) -> User:
        """Decode, validate, and hydrate a user from a bearer token."""
        payload = decode_access_token(token, secret=self._settings.jwt_secret_key)
        if payload.token_id in self._revoked_token_ids:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")

        record = self._users.get(payload.subject)
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user identity.")

        return self.hydrate_user(record)

    def revoke_token(self, token: str) -> None:
        """Store token id in an in-memory denylist for explicit logout support."""
        payload = decode_access_token(token, secret=self._settings.jwt_secret_key)
        self._revoked_token_ids.add(payload.token_id)
