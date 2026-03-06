from __future__ import annotations

from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord


class DocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, DocumentRecord] = {
            "doc-public": DocumentRecord(
                document_id="doc-public",
                title="Public Knowledge Base",
                owner_user_id="u-doc-admin",
                department="knowledge",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Public KB baseline content",
                        metadata=DocumentMetadata(
                            department="knowledge",
                            owner="u-doc-admin",
                            classification="internal",
                            permissions=["role:standard_user"],
                        ),
                    )
                ],
            ),
            "doc-standard": DocumentRecord(
                document_id="doc-standard",
                title="Standard User Handbook",
                owner_user_id="u-standard",
                allowed_users=["u-standard"],
                department="operations",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Standard handbook",
                        metadata=DocumentMetadata(
                            department="operations",
                            owner="u-standard",
                            classification="internal",
                            permissions=["user:u-standard"],
                        ),
                    )
                ],
            ),
            "doc-power": DocumentRecord(
                document_id="doc-power",
                title="Power User SOP",
                owner_user_id="u-power",
                allowed_roles=["power_user"],
                department="engineering",
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Power user SOP",
                        metadata=DocumentMetadata(
                            department="engineering",
                            owner="u-power",
                            classification="internal",
                            permissions=["role:power_user"],
                        ),
                    )
                ],
            ),
            "doc-confidential": DocumentRecord(
                document_id="doc-confidential",
                title="Compliance Incident Report",
                owner_user_id="u-compliance",
                classification="confidential",
                department="compliance",
                allowed_roles=["compliance_officer", "system_administrator", "super_administrator"],
                versions=[
                    DocumentVersionRecord(
                        version=1,
                        content="Confidential compliance report",
                        metadata=DocumentMetadata(
                            department="compliance",
                            owner="u-compliance",
                            classification="confidential",
                            permissions=[
                                "role:compliance_officer",
                                "role:system_administrator",
                                "role:super_administrator",
                            ],
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
        self._documents[record.document_id] = record
        return record

    def delete(self, document_id: str) -> bool:
        if document_id not in self._documents:
            return False
        del self._documents[document_id]
        return True
