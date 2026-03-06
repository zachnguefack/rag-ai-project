from __future__ import annotations

from datetime import datetime, timezone

from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord


class DocumentRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._documents: dict[str, DocumentRecord] = {
            "doc-ops": DocumentRecord(
                document_id="doc-ops",
                title="Operations Handbook",
                department_id="dept-operations",
                document_type="handbook",
                owner="u-standard",
                classification="internal",
                status="active",
                created_at=now,
                updated_at=now,
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Standard operations handbook",
                        metadata=DocumentMetadata(
                            department_id="dept-operations",
                            owner="u-standard",
                            classification="internal",
                            document_type="handbook",
                            status="active",
                        ),
                    )
                ],
            ),
            "doc-eng": DocumentRecord(
                document_id="doc-eng",
                title="Engineering SOP",
                department_id="dept-engineering",
                document_type="sop",
                owner="u-power",
                classification="internal",
                status="active",
                created_at=now,
                updated_at=now,
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Engineering SOP",
                        metadata=DocumentMetadata(
                            department_id="dept-engineering",
                            owner="u-power",
                            classification="internal",
                            document_type="sop",
                            status="active",
                        ),
                    )
                ],
            ),
            "doc-compliance": DocumentRecord(
                document_id="doc-compliance",
                title="Compliance Incident Report",
                department_id="dept-compliance",
                document_type="report",
                owner="u-compliance",
                classification="confidential",
                status="active",
                created_at=now,
                updated_at=now,
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Confidential compliance report",
                        metadata=DocumentMetadata(
                            department_id="dept-compliance",
                            owner="u-compliance",
                            classification="confidential",
                            document_type="report",
                            status="active",
                        ),
                    )
                ],
            ),
        }

    def get(self, document_id: str) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def list(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def list_by_department(self, department_id: str) -> list[DocumentRecord]:
        return [doc for doc in self._documents.values() if doc.department_id == department_id]

    def upsert(self, record: DocumentRecord) -> DocumentRecord:
        self._documents[record.document_id] = record
        return record

    def delete(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False
        del self._documents[document_id]
        return True
