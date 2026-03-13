"""Document scope computation service for department + explicit grant access control."""

from __future__ import annotations

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository


class ScopeBuilderService:
    """Build effective authorized document ids for a user."""
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        user_document_access_repository: UserDocumentAccessRepository | None = None,
        user_department_access_repository: UserDepartmentAccessRepository | None = None,
    ) -> None:
        self._documents = document_repository or DocumentRepository()
        self._access = user_document_access_repository or UserDocumentAccessRepository()
        self._department_access = user_department_access_repository or UserDepartmentAccessRepository()

    def build_authorized_scope(self, *, user_id: str, department_ids: list[str]) -> list[str]:
        """Compute document scope as department union explicit grants minus revocations."""
        user_department_ids = {record.department_id for record in self._department_access.list_departments_for_user(user_id)}
        effective_departments = user_department_ids | set(department_ids)
        dept_document_ids: set[str] = set()
        for department_id in effective_departments:
            dept_document_ids.update(doc.document_id for doc in self._documents.list_by_department(department_id))
        grant_records = self._access.list_for_user(user_id)
        explicit_grants = {record.document_id for record in grant_records if record.is_active}
        revoked_grants = {record.document_id for record in grant_records if not record.is_active}
        final_scope = (dept_document_ids | explicit_grants) - revoked_grants
        return sorted(final_scope)
