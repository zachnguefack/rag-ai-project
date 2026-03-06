from __future__ import annotations

from datetime import datetime, timezone

from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord


class DocumentRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._documents: dict[str, DocumentRecord] = {
            "doc-public": DocumentRecord(
                document_id="doc-public",
                title="Public Knowledge Base",
                document_type="knowledge_base",
                owner_user_id="u-doc-admin",
                department="knowledge",
                status="approved",
                versions=[
                    DocumentVersionRecord(
                        version_id="doc-public-v1",
                        document_id="doc-public",
                        version_number=1,
                        content="Public KB baseline content",
                        storage_path="/data/doc-public/v1.txt",
                        checksum="sha256:doc-public-v1",
                        indexed=True,
                        approved_at=now,
                        metadata=DocumentMetadata(
                            department="knowledge",
                            owner="u-doc-admin",
                            classification="internal",
                            status="approved",
                            permissions=["role:standard_user"],
                            allowed_roles=["standard_user"],
                        ),
                    )
                ],
            ),
            "doc-standard": DocumentRecord(
                document_id="doc-standard",
                title="Standard User Handbook",
                document_type="handbook",
                owner_user_id="u-standard",
                allowed_users=["u-standard"],
                allowed_departments=["operations"],
                department="operations",
                status="approved",
                versions=[
                    DocumentVersionRecord(
                        version_id="doc-standard-v1",
                        document_id="doc-standard",
                        version_number=1,
                        content="Standard handbook",
                        storage_path="/data/doc-standard/v1.txt",
                        checksum="sha256:doc-standard-v1",
                        indexed=True,
                        approved_at=now,
                        metadata=DocumentMetadata(
                            department="operations",
                            owner="u-standard",
                            classification="internal",
                            status="approved",
                            permissions=["user:u-standard"],
                            allowed_user_ids=["u-standard"],
                            allowed_departments=["operations"],
                        ),
                    )
                ],
            ),
            "doc-power": DocumentRecord(
                document_id="doc-power",
                title="Power User SOP",
                document_type="sop",
                owner_user_id="u-power",
                allowed_roles=["power_user"],
                department="engineering",
                status="approved",
                versions=[
                    DocumentVersionRecord(
                        version_id="doc-power-v1",
                        document_id="doc-power",
                        version_number=1,
                        content="Power user SOP",
                        storage_path="/data/doc-power/v1.txt",
                        checksum="sha256:doc-power-v1",
                        indexed=True,
                        approved_at=now,
                        metadata=DocumentMetadata(
                            department="engineering",
                            owner="u-power",
                            classification="internal",
                            status="approved",
                            permissions=["role:power_user"],
                            allowed_roles=["power_user"],
                        ),
                    )
                ],
            ),
            "doc-confidential": DocumentRecord(
                document_id="doc-confidential",
                title="Compliance Incident Report",
                document_type="incident_report",
                owner_user_id="u-compliance",
                classification="confidential",
                status="approved",
                department="compliance",
                allowed_roles=["compliance_officer", "system_administrator", "super_administrator"],
                allowed_departments=["compliance"],
                versions=[
                    DocumentVersionRecord(
                        version_id="doc-confidential-v1",
                        document_id="doc-confidential",
                        version_number=1,
                        content="Confidential compliance report",
                        storage_path="/data/doc-confidential/v1.txt",
                        checksum="sha256:doc-confidential-v1",
                        indexed=True,
                        approved_at=now,
                        metadata=DocumentMetadata(
                            department="compliance",
                            owner="u-compliance",
                            classification="confidential",
                            status="approved",
                            permissions=[
                                "role:compliance_officer",
                                "role:system_administrator",
                                "role:super_administrator",
                            ],
                            allowed_roles=["compliance_officer", "system_administrator", "super_administrator"],
                            allowed_departments=["compliance"],
                        ),
                    )
                ],
            ),
        }

    def get(self, document_id: str) -> DocumentRecord | None:
        return self._documents.get(document_id)

    def list(self) -> list[DocumentRecord]:
        return list(self._documents.values())

    def upsert(self, record: DocumentRecord) -> DocumentRecord:
        record.updated_at = datetime.now(timezone.utc)
        self._documents[record.document_id] = record
        return record

    def delete(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False
        del self._documents[document_id]
        return True
