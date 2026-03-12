from __future__ import annotations

import secrets

from app.database.sqlite import SQLiteStore, dumps_json, get_default_sqlite_store, loads_json
from app.models.domain.user import User
from app.models.persistence.user import UserRecord
from app.security.policies import RoleName


class UserRepository:
    """SQLite-backed user repository."""

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_default_sqlite_store()

    @staticmethod
    def _row_to_record(row) -> UserRecord:
        return UserRecord(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            department_id=row["department_id"] or "",
            department_ids=loads_json(row["department_ids_json"], []),
            is_active=bool(row["is_active"]),
            roles=[RoleName(role) for role in loads_json(row["roles_json"], [])],
            document_allow_list=loads_json(row["document_allow_list_json"], []),
        )

    def _upsert(self, record: UserRecord) -> UserRecord:
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    user_id, username, email, password_hash, department_id,
                    department_ids_json, is_active, roles_json, document_allow_list_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    email=excluded.email,
                    password_hash=excluded.password_hash,
                    department_id=excluded.department_id,
                    department_ids_json=excluded.department_ids_json,
                    is_active=excluded.is_active,
                    roles_json=excluded.roles_json,
                    document_allow_list_json=excluded.document_allow_list_json
                """,
                (
                    record.user_id,
                    record.username,
                    str(record.email),
                    record.password_hash,
                    record.department_id,
                    dumps_json(record.department_ids),
                    1 if record.is_active else 0,
                    dumps_json([role.value for role in record.roles]),
                    dumps_json(record.document_allow_list),
                ),
            )
        return self.get(record.user_id) or record

    def get(self, user_id: str) -> UserRecord | None:
        with self._store.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_username(self, username: str) -> UserRecord | None:
        with self._store.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return self._row_to_record(row) if row else None

    def get_by_email(self, email: str) -> UserRecord | None:
        with self._store.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return self._row_to_record(row) if row else None

    def count(self) -> int:
        with self._store.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        return int(row["total"])

    def list(self) -> list[UserRecord]:
        with self._store.connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY username ASC").fetchall()
        return [self._row_to_record(row) for row in rows]

    def set_roles(self, user_id: str, roles: list[RoleName]) -> UserRecord | None:
        record = self.get(user_id)
        if record is None:
            return None
        record.roles = roles
        return self._upsert(record)

    def set_password_hash(self, user_id: str, password_hash: str) -> UserRecord | None:
        record = self.get(user_id)
        if record is None:
            return None
        record.password_hash = password_hash
        return self._upsert(record)

    def set_active(self, user_id: str, is_active: bool) -> UserRecord | None:
        record = self.get(user_id)
        if record is None:
            return None
        record.is_active = is_active
        return self._upsert(record)

    def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
    ) -> UserRecord | None:
        record = self.get(user_id)
        if record is None:
            return None
        if username is not None:
            record.username = username
        if email is not None:
            record.email = email
        if is_active is not None:
            record.is_active = is_active
        return self._upsert(record)

    def set_department(self, user_id: str, department_id: str) -> UserRecord | None:
        record = self.get(user_id)
        if record is None:
            return None
        record.department_id = department_id
        record.department_ids = [department_id]
        return self._upsert(record)

    def create(
        self,
        username: str,
        email: str,
        password_hash: str,
        roles: list[RoleName],
        department_id: str = "",
    ) -> UserRecord:
        user_id = f"u-{secrets.token_hex(8)}"
        return self.create_with_id(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            roles=roles,
            department_id=department_id,
        )

    def create_with_id(
        self,
        *,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        roles: list[RoleName],
        department_id: str = "",
    ) -> UserRecord:
        record = UserRecord(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            roles=roles,
            department_id=department_id,
            department_ids=[department_id] if department_id else [],
        )
        return self._upsert(record)

    def hydrate(self, record: UserRecord, roles: tuple) -> User:
        return User(
            user_id=record.user_id,
            username=record.username,
            email=str(record.email),
            department_id=record.department_id,
            department_ids=tuple(record.department_ids),
            is_active=record.is_active,
            roles=roles,
            document_allow_list=frozenset(record.document_allow_list),
        )
