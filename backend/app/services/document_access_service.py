from __future__ import annotations

from dataclasses import dataclass

from app.database.repositories.document_repo import DocumentRepository
from app.models.domain.user import User
from app.models.persistence.document import DocumentRecord
from app.security.policies import DOCUMENT_GLOBAL_ACCESS_ROLES

CLASSIFICATION_ORDER = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3, "secret": 4}
ALLOWED_DOCUMENT_STATUSES = {"approved", "indexed"}


@dataclass(slots=True)
class DocumentAccessDecision:
    document_id: str
    allowed: bool
    reason: str


class DocumentAccessService:
    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._documents = document_repository or DocumentRepository()

    def can_access_document(self, user: User, document: DocumentRecord) -> DocumentAccessDecision:
        if document.status not in ALLOWED_DOCUMENT_STATUSES:
            return DocumentAccessDecision(document.document_id, False, "Document status not in allowed set.")

        if not self._classification_allowed(user.classification_level, document.classification):
            return DocumentAccessDecision(document.document_id, False, "User classification clearance is insufficient.")

        if user.role_names & DOCUMENT_GLOBAL_ACCESS_ROLES:
            return DocumentAccessDecision(document.document_id, True, "Global-access admin role.")

        if document.owner_user_id == user.user_id:
            return DocumentAccessDecision(document.document_id, True, "Document owner.")

        if user.user_id in document.allowed_users or document.document_id in user.document_allow_list:
            return DocumentAccessDecision(document.document_id, True, "Explicit user assignment.")

        if user.department == document.department or user.department in document.allowed_departments:
            return DocumentAccessDecision(document.document_id, True, "Department scope matched.")

        if document.site_scope and document.site_scope in user.allowed_document_scopes:
            return DocumentAccessDecision(document.document_id, True, "Document site scope allowed.")

        user_roles = {role.value for role in user.role_names}
        if user_roles & set(document.allowed_roles):
            return DocumentAccessDecision(document.document_id, True, "Role-based ACL matched.")

        return DocumentAccessDecision(document.document_id, False, "Deny-by-default: no access rule matched.")

    def authorized_document_ids(self, user: User) -> list[str]:
        authorized_ids: list[str] = []
        for document in self._documents.list():
            if self.can_access_document(user, document).allowed:
                authorized_ids.append(document.document_id)
        return authorized_ids

    @staticmethod
    def _classification_allowed(user_classification: str, document_classification: str) -> bool:
        user_level = CLASSIFICATION_ORDER.get((user_classification or "internal").lower(), 1)
        doc_level = CLASSIFICATION_ORDER.get((document_classification or "internal").lower(), 1)
        return user_level >= doc_level
