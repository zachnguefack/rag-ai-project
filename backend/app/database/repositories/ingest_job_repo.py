from __future__ import annotations

import threading

from app.models.persistence.ingest_job import IngestJobRecord


class IngestJobRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, IngestJobRecord] = {}

    def upsert(self, job: IngestJobRecord) -> IngestJobRecord:
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> IngestJobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[IngestJobRecord]:
        with self._lock:
            return list(self._jobs.values())
