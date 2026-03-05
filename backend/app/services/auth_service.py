from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from app.config.settings import BackendSettings
from app.database.repositories.role_repo import RoleRepository
from app.database.repositories.user_repo import UserRepository
from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.jwt import create_access_token, decode_access_token
from app.security.password import hash_password, verify_password
from app.security.policies import RoleName


class AuthService:
    def __init__(
        self,
        settings: BackendSettings,
        user_repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
    ) -> None:
        self._settings = settings
        self._users = user_repository or UserRepository()
        self._roles = role_repository or RoleRepository()
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

    def hydrate_user(self, record: UserRecord) -> User:
        roles = tuple(self._roles.get(role_name) for role_name in record.roles)
        user = self._users.hydrate(record, roles)
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled.")
        return user

    def issue_access_token(self, user: UserRecord) -> tuple[str, datetime]:
        return create_access_token(
            subject=user.user_id,
            secret=self._settings.jwt_secret_key,
            expires_in_minutes=self._settings.jwt_access_token_expire_minutes,
        )

    def resolve_user_from_token(self, token: str) -> User:
        payload = decode_access_token(token, secret=self._settings.jwt_secret_key)
        if payload.token_id in self._revoked_token_ids:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")

        record = self._users.get(payload.subject)
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user identity.")

        return self.hydrate_user(record)

    def revoke_token(self, token: str) -> None:
        payload = decode_access_token(token, secret=self._settings.jwt_secret_key)
        self._revoked_token_ids.add(payload.token_id)
