from __future__ import annotations

from app.services.ingestion_service import IngestionService


def run_ingestion_task(service: IngestionService, *, force_reindex: bool = False) -> dict[str, int | bool]:
    job = service.run_incremental_indexing(force_reindex=force_reindex)
    return {
        "indexed_files": job.indexed_files,
        "indexed_chunks": job.indexed_chunks,
        "removed_files": job.removed_files,
        "reused_existing_index": job.reused_existing_index,
    }
