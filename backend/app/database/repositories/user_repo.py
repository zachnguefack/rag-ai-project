from __future__ import annotations

from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.policies import RoleName


class UserRepository:
    """In-memory user store. Replace with a DB-backed repository in production."""

    def __init__(self) -> None:
        self._records: dict[str, UserRecord] = {
            "u-standard": UserRecord(
                user_id="u-standard",
                username="standard.analyst",
                email="standard.analyst@example.com",
                roles=[RoleName.STANDARD_USER],
                document_allow_list=["doc-public", "doc-standard"],
            ),
            "u-power": UserRecord(
                user_id="u-power",
                username="power.author",
                email="power.author@example.com",
                roles=[RoleName.POWER_USER],
                document_allow_list=["doc-public", "doc-power"],
            ),
            "u-doc-admin": UserRecord(
                user_id="u-doc-admin",
                username="doc.admin",
                email="doc.admin@example.com",
                roles=[RoleName.DOCUMENT_ADMINISTRATOR],
            ),
            "u-compliance": UserRecord(
                user_id="u-compliance",
                username="compliance.officer",
                email="compliance.officer@example.com",
                roles=[RoleName.COMPLIANCE_OFFICER],
            ),
            "u-sys-admin": UserRecord(
                user_id="u-sys-admin",
                username="sys.admin",
                email="sys.admin@example.com",
                roles=[RoleName.SYSTEM_ADMINISTRATOR],
            ),
            "u-super-admin": UserRecord(
                user_id="u-super-admin",
                username="super.admin",
                email="super.admin@example.com",
                roles=[RoleName.SUPER_ADMINISTRATOR],
            ),
        }

    def get(self, user_id: str) -> UserRecord | None:
        return self._records.get(user_id)

    def hydrate(self, record: UserRecord, roles: tuple) -> User:
        return User(
            user_id=record.user_id,
            username=record.username,
            email=str(record.email),
            is_active=record.is_active,
            roles=roles,
            document_allow_list=frozenset(record.document_allow_list),
        )
