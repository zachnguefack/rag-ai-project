from __future__ import annotations

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository


class ScopeBuilderService:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        user_document_access_repository: UserDocumentAccessRepository | None = None,
    ) -> None:
        self._documents = document_repository or DocumentRepository()
        self._access = user_document_access_repository or UserDocumentAccessRepository()

    def build_authorized_scope(self, *, user_id: str, department_id: str) -> list[str]:
        dept_document_ids = {
            doc.document_id for doc in self._documents.list_by_department(department_id)
        }
        grant_records = self._access.list_for_user(user_id)
        explicit_grants = {record.document_id for record in grant_records if record.is_active}
        revoked_grants = {record.document_id for record in grant_records if not record.is_active}
        final_scope = (dept_document_ids | explicit_grants) - revoked_grants
        return sorted(final_scope)
