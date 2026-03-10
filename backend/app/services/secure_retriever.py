from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.models.domain.user import User
from app.rag_engine.retrieval.filters import combine_metadata_filters, department_id_filter, document_id_filter
from app.services.document_access_service import DocumentAccessService
from app.services.retrieval_service import RetrievalService


class SecureRetriever:
    def __init__(self, retrieval_service: RetrievalService, access_service: DocumentAccessService) -> None:
        self._retrieval = retrieval_service
        self._access_service = access_service

    def retrieve(
        self,
        *,
        question: str,
        user: User,
        mode: str,
        strict_document_scope: bool | None,
        department_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        user_departments = set(user.effective_department_ids)
        if department_id is not None and department_id not in user_departments:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department access denied for retrieval scope.",
            )

        effective_departments = [department_id] if department_id is not None else sorted(user_departments)
        authorized_document_ids = self._access_service.compute_authorized_document_ids(user)
        if document_ids is not None:
            scoped_document_ids = sorted(set(authorized_document_ids) & set(document_ids))
        else:
            scoped_document_ids = authorized_document_ids

        department_filter = department_id_filter(effective_departments) if effective_departments else None
        doc_filter = document_id_filter(scoped_document_ids)
        metadata_filter = combine_metadata_filters(department_filter, doc_filter)
        result = self._retrieval.query(
            question=question,
            mode=mode,
            strict_document_scope=strict_document_scope,
            metadata_filter=metadata_filter,
        )

        # Defense in depth: strip citations that are not part of authorized scope.
        allowed = set(scoped_document_ids)
        safe_citations: list[Any] = []
        for citation in result.get("citations", []):
            if isinstance(citation, dict):
                document_label = str(citation.get("document", ""))
                if document_label in allowed:
                    safe_citations.append(citation)
                continue
            citation_text = str(citation)
            if any(doc_id in citation_text for doc_id in allowed):
                safe_citations.append(citation)
        result["citations"] = safe_citations
        return result
