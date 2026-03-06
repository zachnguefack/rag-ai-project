from __future__ import annotations

from fastapi import HTTPException, status

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.domain.user import User
from app.models.persistence.user_document_access import UserDocumentAccessRecord
from app.security.policies import Permission
from app.services.rbac_service import RBACService
from app.services.scope_builder_service import ScopeBuilderService


class DocumentAccessService:
    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        user_document_access_repository: UserDocumentAccessRepository | None = None,
        scope_builder: ScopeBuilderService | None = None,
        rbac_service: RBACService | None = None,
    ) -> None:
        self._documents = document_repository or DocumentRepository()
        self._access = user_document_access_repository or UserDocumentAccessRepository()
        self._scope_builder = scope_builder or ScopeBuilderService(
            document_repository=self._documents,
            user_document_access_repository=self._access,
        )
        self._rbac = rbac_service or RBACService(document_repository=self._documents)

    def compute_authorized_document_ids(self, user: User) -> list[str]:
        return self._scope_builder.build_authorized_scope(user_id=user.user_id, department_id=user.department_id)

    def can_access_document(self, user: User, document_id: str) -> bool:
        if self._rbac.validate_permission(user, Permission.READ_DOCUMENT).granted is False:
            return False
        document = self._documents.get(document_id)
        if document is None:
            return False
        return document_id in self.compute_authorized_document_ids(user)

    def enforce_document_access(self, user: User, document_id: str) -> None:
        self._rbac.enforce_permission(user, Permission.READ_DOCUMENT)
        document = self._documents.get(document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        if not self.can_access_document(user, document_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: document is outside authorized scope.")

    def grant_document_access(self, *, user_id: str, document_id: str, granted_by: str) -> UserDocumentAccessRecord:
        if self._documents.get(document_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
        return self._access.upsert_grant(user_id=user_id, document_id=document_id, granted_by=granted_by)

    def revoke_document_access(self, *, user_id: str, document_id: str) -> UserDocumentAccessRecord:
        record = self._access.revoke_grant(user_id=user_id, document_id=document_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document grant not found.")
        return record

    def list_document_access(self, user_id: str) -> list[UserDocumentAccessRecord]:
        return self._access.list_for_user(user_id)
