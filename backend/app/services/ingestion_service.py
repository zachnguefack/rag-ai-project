from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.database.repositories.ingest_job_repo import IngestJobRepository
from app.models.persistence.ingest_job import IngestJobRecord
from app.services.rag_service import RAGApplicationService


class IngestionService:
    def __init__(self, rag_service: RAGApplicationService, ingest_job_repo: IngestJobRepository | None = None) -> None:
        self._rag_service = rag_service
        self._jobs = ingest_job_repo or IngestJobRepository()

    def run_incremental_indexing(self, *, force_reindex: bool = False, document_id: str | None = None) -> IngestJobRecord:
        job = IngestJobRecord(job_id=str(uuid4()), document_id=document_id, status="running")
        self._jobs.upsert(job)
        try:
            summary = self._rag_service.run_indexing(force_reindex=force_reindex)
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.indexed_files = summary["indexed_files"]
            job.indexed_chunks = summary["indexed_chunks"]
            job.removed_files = summary["removed_files"]
            job.reused_existing_index = summary["reused_existing_index"]
        except Exception as exc:  # pragma: no cover
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            raise
        finally:
            self._jobs.upsert(job)
        return job
