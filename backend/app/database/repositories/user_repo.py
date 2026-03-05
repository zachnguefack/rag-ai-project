from __future__ import annotations

import secrets

from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.password import hash_password
from app.security.policies import RoleName


class UserRepository:
    """In-memory user store. Replace with a DB-backed repository in production."""

    def __init__(self) -> None:
        default_password_hash = hash_password("ChangeMe123!")
        self._records: dict[str, UserRecord] = {
            "u-standard": UserRecord(
                user_id="u-standard",
                username="standard.analyst",
                email="standard.analyst@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.STANDARD_USER],
                document_allow_list=["doc-public", "doc-standard"],
            ),
            "u-power": UserRecord(
                user_id="u-power",
                username="power.author",
                email="power.author@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.POWER_USER],
                document_allow_list=["doc-public", "doc-power"],
            ),
            "u-doc-admin": UserRecord(
                user_id="u-doc-admin",
                username="doc.admin",
                email="doc.admin@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.DOCUMENT_ADMINISTRATOR],
            ),
            "u-compliance": UserRecord(
                user_id="u-compliance",
                username="compliance.officer",
                email="compliance.officer@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.COMPLIANCE_OFFICER],
            ),
            "u-sys-admin": UserRecord(
                user_id="u-sys-admin",
                username="sys.admin",
                email="sys.admin@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.SYSTEM_ADMINISTRATOR],
            ),
            "u-super-admin": UserRecord(
                user_id="u-super-admin",
                username="super.admin",
                email="super.admin@example.com",
                password_hash=default_password_hash,
                roles=[RoleName.SUPER_ADMINISTRATOR],
            ),
        }

    def get(self, user_id: str) -> UserRecord | None:
        return self._records.get(user_id)

    def get_by_username(self, username: str) -> UserRecord | None:
        return next((record for record in self._records.values() if record.username == username), None)

    def get_by_email(self, email: str) -> UserRecord | None:
        return next((record for record in self._records.values() if str(record.email) == email), None)


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
