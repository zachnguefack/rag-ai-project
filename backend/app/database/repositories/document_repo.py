from __future__ import annotations

from datetime import datetime

from app.database.sqlite import SQLiteStore, get_default_sqlite_store, dumps_json, loads_json
from app.models.persistence.document import DocumentRecord, DocumentVersionRecord


class DocumentRepository:
    def __init__(self, store: SQLiteStore | None = None) -> None:
        self._store = store or get_default_sqlite_store()

    def _row_to_record(self, row) -> DocumentRecord:
        versions = [DocumentVersionRecord.model_validate(item) for item in loads_json(row["versions_json"], [])]
        return DocumentRecord(
            id=row["id"],
            document_id=row["document_id"],
            title=row["title"],
            department_id=row["department_id"],
            owner=row["owner"],
            classification=row["classification"],
            document_type=row["document_type"],
            status=row["status"],
            original_filename=row["original_filename"] or "",
            stored_filename=row["stored_filename"] or "",
            storage_path=row["storage_path"] or "",
            content_type=row["content_type"] or "",
            size_bytes=int(row["size_bytes"] or 0),
            checksum=row["checksum"] or "",
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
            indexing_status=row["indexing_status"] or "pending",
            last_indexed_at=datetime.fromisoformat(row["last_indexed_at"]) if row["last_indexed_at"] else None,
            created_at=datetime.fromisoformat(row["uploaded_at"]),
            updated_at=datetime.fromisoformat(row["uploaded_at"]),
            versions=versions,
        )

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._store.connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def list(self) -> list[DocumentRecord]:
        with self._store.connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [self._row_to_record(r) for r in rows]

    def list_by_department(self, department_id: str) -> list[DocumentRecord]:
        with self._store.connection() as conn:
            rows = conn.execute("SELECT * FROM documents WHERE department_id=? ORDER BY uploaded_at DESC", (department_id,)).fetchall()
        return [self._row_to_record(r) for r in rows]

    def upsert(self, record: DocumentRecord) -> DocumentRecord:
        uploaded_at = (record.uploaded_at or record.created_at).isoformat()
        with self._store.connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    document_id, title, department_id, owner, classification, document_type, status,
                    original_filename, stored_filename, storage_path, content_type, size_bytes, checksum,
                    uploaded_at, indexing_status, last_indexed_at, metadata_json, versions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    title=excluded.title,
                    department_id=excluded.department_id,
                    owner=excluded.owner,
                    classification=excluded.classification,
                    document_type=excluded.document_type,
                    status=excluded.status,
                    original_filename=excluded.original_filename,
                    stored_filename=excluded.stored_filename,
                    storage_path=excluded.storage_path,
                    content_type=excluded.content_type,
                    size_bytes=excluded.size_bytes,
                    checksum=excluded.checksum,
                    uploaded_at=excluded.uploaded_at,
                    indexing_status=excluded.indexing_status,
                    last_indexed_at=excluded.last_indexed_at,
                    metadata_json=excluded.metadata_json,
                    versions_json=excluded.versions_json
                """,
                (
                    record.document_id,
                    record.title,
                    record.department_id,
                    record.owner,
                    record.classification,
                    record.document_type,
                    record.status,
                    record.original_filename,
                    record.stored_filename,
                    record.storage_path,
                    record.content_type,
                    record.size_bytes,
                    record.checksum,
                    uploaded_at,
                    record.indexing_status,
                    record.last_indexed_at.isoformat() if record.last_indexed_at else None,
                    dumps_json({"department_id": record.department_id}),
                    dumps_json([v.model_dump(mode="json") for v in record.versions]),
                ),
            )
        return self.get(record.document_id) or record

    def delete(self, document_id: str) -> bool:
        with self._store.connection() as conn:
            cur = conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
        return cur.rowcount > 0
