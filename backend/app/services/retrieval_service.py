from __future__ import annotations

from typing import Any

from app.models.domain.user import User
from app.services.rag_service import RAGApplicationService
from app.services.scope_builder_service import ScopeBuilderService


class RetrievalService:
    """Application-level retrieval orchestration facade."""

    def __init__(self, rag_service: RAGApplicationService, scope_builder: ScopeBuilderService) -> None:
        self._rag_service = rag_service
        self._scope_builder = scope_builder

    def query(self, *, user: User, question: str, mode: str, strict_document_scope: bool | None, metadata_filter: dict[str, Any] | None) -> dict:
        scope = self._scope_builder.build_scope(user)
        result = self._rag_service.answer(
            user=user,
            question=question,
            mode=mode,
            strict_document_scope=strict_document_scope,
            metadata_filter=metadata_filter,
        )
        result["authorized_document_ids_count"] = len(scope.authorized_document_ids)
        return result
