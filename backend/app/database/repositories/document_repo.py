from __future__ import annotations

from app.models.persistence.document import DocumentRecord


class DocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, DocumentRecord] = {
            "doc-public": DocumentRecord(
                document_id="doc-public",
                title="Public Knowledge Base",
                owner_user_id="u-doc-admin",
            ),
            "doc-standard": DocumentRecord(
                document_id="doc-standard",
                title="Standard User Handbook",
                owner_user_id="u-standard",
                allowed_users=["u-standard"],
            ),
            "doc-power": DocumentRecord(
                document_id="doc-power",
                title="Power User SOP",
                owner_user_id="u-power",
                allowed_roles=["power_user"],
            ),
            "doc-confidential": DocumentRecord(
                document_id="doc-confidential",
                title="Compliance Incident Report",
                owner_user_id="u-compliance",
                classification="confidential",
                allowed_roles=["compliance_officer", "system_administrator", "super_administrator"],
            ),
        }

    def get(self, document_id: str) -> DocumentRecord | None:
        return self._documents.get(document_id)
