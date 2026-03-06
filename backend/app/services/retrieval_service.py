from __future__ import annotations

from typing import Any

from app.services.rag_service import RAGApplicationService


class RetrievalService:
    """Application-level retrieval orchestration facade."""

    def __init__(self, rag_service: RAGApplicationService) -> None:
        self._rag_service = rag_service

    def query(self, *, question: str, mode: str, strict_document_scope: bool | None, metadata_filter: dict[str, Any] | None) -> dict:
        return self._rag_service.answer(
            question=question,
            mode=mode,
            strict_document_scope=strict_document_scope,
            metadata_filter=metadata_filter,
        )
