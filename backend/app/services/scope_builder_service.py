from __future__ import annotations

from dataclasses import dataclass

from app.models.domain.user import User
from app.services.document_access_service import DocumentAccessService


@dataclass(slots=True)
class RetrievalScope:
    authorized_document_ids: list[str]


class ScopeBuilderService:
    def __init__(self, document_access_service: DocumentAccessService) -> None:
        self._document_access = document_access_service

    def build_scope(self, user: User) -> RetrievalScope:
        return RetrievalScope(authorized_document_ids=self._document_access.authorized_document_ids(user))
