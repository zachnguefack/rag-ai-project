from __future__ import annotations

from datetime import datetime, timezone

from app.database.sqlite import SQLiteStore, get_default_sqlite_store
from app.models.persistence.user_document_access import UserDocumentAccessRecord


class UserDocumentAccessRepository:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_default_sqlite_store()

    @staticmethod
    def _row_to_record(row) -> UserDocumentAccessRecord:
        return UserDocumentAccessRecord(
            id=row["id"],
            user_id=row["user_id"],
            document_id=row["document_id"],
            granted_by=row["granted_by"],
            granted_at=datetime.fromisoformat(row["granted_at"]),
            revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
            is_active=bool(row["is_active"]),
        )

    def get(self, user_id: str, document_id: str) -> UserDocumentAccessRecord | None:
        with self._store.connection() as conn:
            row = conn.execute(
                "SELECT id, user_id, document_id, granted_by, granted_at, revoked_at, is_active FROM user_document_access WHERE user_id=? AND document_id=?",
                (user_id, document_id),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_for_user(self, user_id: str) -> list[UserDocumentAccessRecord]:
        with self._store.connection() as conn:
            rows = conn.execute(
                "SELECT id, user_id, document_id, granted_by, granted_at, revoked_at, is_active FROM user_document_access WHERE user_id=?",
                (user_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_for_document(self, document_id: str) -> list[UserDocumentAccessRecord]:
        with self._store.connection() as conn:
            rows = conn.execute(
                "SELECT id, user_id, document_id, granted_by, granted_at, revoked_at, is_active FROM user_document_access WHERE document_id=?",
                (document_id,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def upsert_grant(self, user_id: str, document_id: str, granted_by: str) -> UserDocumentAccessRecord:
        granted_at = datetime.now(timezone.utc).isoformat()
        record_id = f"uda-{user_id}-{document_id}"
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO user_document_access (id, user_id, document_id, granted_by, granted_at, revoked_at, is_active)
                VALUES (?, ?, ?, ?, ?, NULL, 1)
                ON CONFLICT(user_id, document_id) DO UPDATE SET
                    granted_by=excluded.granted_by,
                    granted_at=excluded.granted_at,
                    revoked_at=NULL,
                    is_active=1
                """,
                (record_id, user_id, document_id, granted_by, granted_at),
            )
        return self.get(user_id, document_id) or UserDocumentAccessRecord(
            id=record_id,
            user_id=user_id,
            document_id=document_id,
            granted_by=granted_by,
            granted_at=datetime.fromisoformat(granted_at),
            revoked_at=None,
            is_active=True,
        )

    def revoke_grant(self, user_id: str, document_id: str) -> UserDocumentAccessRecord | None:
        revoked_at = datetime.now(timezone.utc).isoformat()
        with self._store.connection() as conn:
            conn.execute(
                """
                UPDATE user_document_access
                SET is_active=0, revoked_at=?
                WHERE user_id=? AND document_id=?
                """,
                (revoked_at, user_id, document_id),
            )
        return self.get(user_id, document_id)

    def delete_for_document(self, document_id: str) -> int:
        with self._store.connection() as conn:
            cur = conn.execute("DELETE FROM user_document_access WHERE document_id=?", (document_id,))
        return cur.rowcount
