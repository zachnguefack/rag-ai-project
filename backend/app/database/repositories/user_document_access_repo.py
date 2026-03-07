from __future__ import annotations

from datetime import datetime, timezone

from app.models.persistence.user_document_access import UserDocumentAccessRecord


class UserDocumentAccessRepository:
    _records: dict[tuple[str, str], UserDocumentAccessRecord] = {}

    def get(self, user_id: str, document_id: str) -> UserDocumentAccessRecord | None:
        return self._records.get((user_id, document_id))

    def list_for_user(self, user_id: str) -> list[UserDocumentAccessRecord]:
        return [record for (uid, _), record in self._records.items() if uid == user_id]


    def list_for_document(self, document_id: str) -> list[UserDocumentAccessRecord]:
        return [record for (_, doc_id), record in self._records.items() if doc_id == document_id]

    def upsert_grant(self, user_id: str, document_id: str, granted_by: str) -> UserDocumentAccessRecord:
        key = (user_id, document_id)
        existing = self._records.get(key)
        if existing:
            existing.granted_by = granted_by
            existing.granted_at = datetime.now(timezone.utc)
            existing.revoked_at = None
            existing.is_active = True
            return existing

        record = UserDocumentAccessRecord(
            id=f"uda-{user_id}-{document_id}",
            user_id=user_id,
            document_id=document_id,
            granted_by=granted_by,
        )
        self._records[key] = record
        return record

    def revoke_grant(self, user_id: str, document_id: str) -> UserDocumentAccessRecord | None:
        record = self._records.get((user_id, document_id))
        if record is None:
            return None
        record.is_active = False
        record.revoked_at = datetime.now(timezone.utc)
        return record
