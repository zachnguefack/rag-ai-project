from __future__ import annotations

from datetime import datetime
from app.database.sqlite import SQLiteStore, get_default_sqlite_store
from app.models.persistence.user_department_access import UserDepartmentAccessRecord


class UserDepartmentAccessRepository:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_default_sqlite_store()

    @staticmethod
    def _row_to_record(row) -> UserDepartmentAccessRecord:
        return UserDepartmentAccessRecord(
            id=row["id"],
            user_id=row["user_id"],
            department_id=row["department_id"],
            assigned_by=row["assigned_by"],
            assigned_at=datetime.fromisoformat(row["assigned_at"]),
        )

    def assign(self, *, user_id: str, department_id: str, assigned_by: str) -> UserDepartmentAccessRecord:
        record_id = f"udep-{user_id}-{department_id}"
        assigned_at = datetime.utcnow().isoformat()
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_department_access (id, user_id, department_id, assigned_by, assigned_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, department_id) DO UPDATE SET
                    assigned_by=excluded.assigned_by,
                    assigned_at=excluded.assigned_at
                """,
                (record_id, user_id, department_id, assigned_by, assigned_at),
            )
            row = conn.execute(
                "SELECT id, user_id, department_id, assigned_by, assigned_at FROM user_department_access WHERE user_id=? AND department_id=?",
                (user_id, department_id),
            ).fetchone()
        return self._row_to_record(row)

    def remove(self, *, user_id: str, department_id: str) -> bool:
        with self._store.connection() as conn:
            cur = conn.execute(
                "DELETE FROM user_department_access WHERE user_id=? AND department_id=?",
                (user_id, department_id),
            )
        return cur.rowcount > 0

    def list_departments_for_user(self, user_id: str) -> list[UserDepartmentAccessRecord]:
        with self._store.connection() as conn:
            rows = conn.execute(
                "SELECT id, user_id, department_id, assigned_by, assigned_at FROM user_department_access WHERE user_id=? ORDER BY department_id",
                (user_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_users_for_department(self, department_id: str) -> list[UserDepartmentAccessRecord]:
        with self._store.connection() as conn:
            rows = conn.execute(
                "SELECT id, user_id, department_id, assigned_by, assigned_at FROM user_department_access WHERE department_id=? ORDER BY user_id",
                (department_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

