from __future__ import annotations

from datetime import datetime

from app.database.sqlite import SQLiteStore, get_default_sqlite_store
from app.models.persistence.ingest_job import IngestJobRecord


class IngestJobRepository:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_default_sqlite_store()

    def upsert(self, job: IngestJobRecord) -> IngestJobRecord:
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO ingest_jobs (job_id, document_id, status, started_at, completed_at, indexed_files, indexed_chunks, removed_files, reused_existing_index, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    document_id=excluded.document_id,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    indexed_files=excluded.indexed_files,
                    indexed_chunks=excluded.indexed_chunks,
                    removed_files=excluded.removed_files,
                    reused_existing_index=excluded.reused_existing_index,
                    error_message=excluded.error_message
                """,
                (
                    job.job_id,
                    job.document_id,
                    job.status,
                    job.started_at.isoformat(),
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.indexed_files,
                    job.indexed_chunks,
                    job.removed_files,
                    1 if job.reused_existing_index else 0,
                    job.error_message,
                ),
            )
        return self.get(job.job_id) or job

    def get(self, job_id: str) -> IngestJobRecord | None:
        with self._store.connection() as conn:
            row = conn.execute("SELECT * FROM ingest_jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            return None
        return IngestJobRecord(
            job_id=row["job_id"],
            document_id=row["document_id"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            indexed_files=int(row["indexed_files"]),
            indexed_chunks=int(row["indexed_chunks"]),
            removed_files=int(row["removed_files"]),
            reused_existing_index=bool(row["reused_existing_index"]),
            error_message=row["error_message"],
        )

    def list(self) -> list[IngestJobRecord]:
        with self._store.connection() as conn:
            rows = conn.execute("SELECT * FROM ingest_jobs ORDER BY started_at DESC").fetchall()
        return [self.get(r["job_id"]) for r in rows if self.get(r["job_id"]) is not None]
