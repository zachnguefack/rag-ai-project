from __future__ import annotations

import secrets

from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.policies import RoleName


class UserRepository:
    """In-memory user store. Replace with a DB-backed repository in production."""

    _records: dict[str, UserRecord] = {}

    def __init__(self) -> None:
        pass

    def get(self, user_id: str) -> UserRecord | None:
        return self._records.get(user_id)

    def get_by_username(self, username: str) -> UserRecord | None:
        return next((record for record in self._records.values() if record.username == username), None)

    def get_by_email(self, email: str) -> UserRecord | None:
        return next((record for record in self._records.values() if str(record.email) == email), None)

    def count(self) -> int:
        return len(self._records)

    def set_roles(self, user_id: str, roles: list[RoleName]) -> UserRecord | None:
        record = self._records.get(user_id)
        if record is None:
            return None
        record.roles = roles
        return record

    def create(self, username: str, email: str, password_hash: str, roles: list[RoleName]) -> UserRecord:
        user_id = f"u-{secrets.token_hex(8)}"
        record = UserRecord(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            roles=roles,
        )
        self._records[user_id] = record
        return record

    def hydrate(self, record: UserRecord, roles: tuple) -> User:
        return User(
            user_id=record.user_id,
            username=record.username,
            email=str(record.email),
            is_active=record.is_active,
            roles=roles,
            document_allow_list=frozenset(record.document_allow_list),
        )
