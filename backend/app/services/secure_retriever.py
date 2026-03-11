from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.models.domain.user import User
from app.rag_engine.retrieval.filters import (
    any_metadata_filter,
    combine_metadata_filters,
    department_id_filter,
    document_id_filter,
    source_path_filter,
)
from app.services.document_access_service import DocumentAccessService
from app.services.retrieval_service import RetrievalService


class SecureRetriever:
    """Retrieval facade that enforces server-side authorization scope before vector search."""

    def __init__(self, retrieval_service: RetrievalService, access_service: DocumentAccessService) -> None:
        self._retrieval = retrieval_service
        self._access_service = access_service

    def _normalize_requested_document_ids(self, document_ids: list[str] | None) -> list[str] | None:
        if document_ids is None:
            return None
        normalized = sorted({str(doc_id).strip() for doc_id in document_ids if str(doc_id).strip()})
        return normalized or []

    @staticmethod
    def _build_allowed_source_paths(user: User, authorized_document_ids: list[str]) -> list[str]:
        explicit_allowlist = {str(path).strip() for path in user.document_allow_list if str(path).strip()}
        if not explicit_allowlist:
            return []

        # Narrow explicit source path allowances to authorized internal document IDs when a mapping exists.
        # Paths without internal IDs remain supported for backward compatibility.
        authorized_markers = {f"/{doc_id}." for doc_id in authorized_document_ids}
        scoped_paths = [
            path
            for path in sorted(explicit_allowlist)
            if not authorized_markers or any(marker in path for marker in authorized_markers)
        ]
        return scoped_paths

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

        requested_document_ids = self._normalize_requested_document_ids(document_ids)
        if requested_document_ids is not None:
            scoped_document_ids = sorted(set(authorized_document_ids) & set(requested_document_ids))
            denied_document_ids = sorted(set(requested_document_ids) - set(scoped_document_ids))
            if denied_document_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="One or more requested document_ids are outside your authorized scope.",
                )
        else:
            scoped_document_ids = authorized_document_ids

        # Enterprise-safe default behavior: normal users cannot query an unrestricted global corpus.
        if not scoped_document_ids:
            return {
                "answer": "No relevant information was found in the available documentation.",
                "mode": mode,
                "source_type": "documents",
                "doc_grounded": False,
                "confidence": {"score": 0.0},
                "citations": [],
            }

        department_filter = department_id_filter(effective_departments) if effective_departments else None
        doc_filter = document_id_filter(scoped_document_ids)
        allowed_source_paths = self._build_allowed_source_paths(user, scoped_document_ids)
        source_filter = source_path_filter(allowed_source_paths) if allowed_source_paths else None
        scope_filter = any_metadata_filter(doc_filter, source_filter)
        metadata_filter = combine_metadata_filters(department_filter, scope_filter)

        result = self._retrieval.query(
            question=question,
            mode=mode,
            strict_document_scope=strict_document_scope,
            metadata_filter=metadata_filter,
        )

        # Defense in depth: strip citations that are not part of authorized internal IDs.
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
