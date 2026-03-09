from __future__ import annotations

from datetime import datetime

from pathlib import Path
import tempfile
from uuid import uuid4

from app.database.sqlite import SQLiteStore
from app.models.persistence.department import DepartmentRecord


class DepartmentRepository:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or SQLiteStore(Path(tempfile.gettempdir()) / f"rag-metadata-{uuid4().hex}.db")

    def list(self) -> list[DepartmentRecord]:
        with self._store.connection() as conn:
            rows = conn.execute(
                "SELECT id, department_id, name, slug, description, created_at, is_active FROM departments ORDER BY slug"
            ).fetchall()
        return [
            DepartmentRecord(
                id=row["id"],
                department_id=row["department_id"],
                name=row["name"],
                slug=row["slug"],
                description=row["description"] or "",
                created_at=datetime.fromisoformat(row["created_at"]),
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def get(self, department_id: str) -> DepartmentRecord | None:
        with self._store.connection() as conn:
            row = conn.execute(
                "SELECT id, department_id, name, slug, description, created_at, is_active FROM departments WHERE department_id=? OR slug=?",
                (department_id, department_id),
            ).fetchone()
        if row is None:
            return None
        return DepartmentRecord(
            id=row["id"],
            department_id=row["department_id"],
            name=row["name"],
            slug=row["slug"],
            description=row["description"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            is_active=bool(row["is_active"]),
        )

    def upsert(self, record: DepartmentRecord) -> DepartmentRecord:
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO departments (department_id, name, slug, description, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(department_id) DO UPDATE SET
                    name=excluded.name,
                    slug=excluded.slug,
                    description=excluded.description,
                    is_active=excluded.is_active
                """,
                (
                    record.department_id,
                    record.name,
                    record.slug,
                    record.description,
                    record.created_at.isoformat(),
                    1 if record.is_active else 0,
                ),
            )
        return self.get(record.department_id) or record

    def delete(self, department_id: str) -> bool:
        with self._store.connection() as conn:
            cur = conn.execute("DELETE FROM departments WHERE department_id=? OR slug=?", (department_id, department_id))
        return cur.rowcount > 0
