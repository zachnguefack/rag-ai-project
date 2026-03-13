"""Authorization-aware retrieval orchestrator for secure RAG queries."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from rag_v2.document_ids import normalize_document_id

from app.models.domain.user import User
from app.rag_engine.retrieval.filters import (
    any_metadata_filter,
    combine_metadata_filters,
    department_id_filter,
    document_id_filter,
    source_filter,
    source_path_filter,
)
from app.services.document_access_service import DocumentAccessService
from app.services.retrieval_service import RetrievalService


LOGGER = logging.getLogger("app.secure_retriever")


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

    @staticmethod
    def _expand_document_id_candidates(document_ids: list[str]) -> list[str]:
        expanded: set[str] = set()
        for value in document_ids:
            raw = str(value).strip()
            if not raw:
                continue
            expanded.add(raw)
            expanded.add(raw.lower())
            expanded.add(raw.replace("-", "_"))
            expanded.add(raw.replace("_", "-"))
            normalized = normalize_document_id(raw)
            if normalized:
                expanded.add(normalized)
                expanded.add(normalized.replace("-", "_"))
        return sorted(item for item in expanded if item)

    @staticmethod
    def _compact_token(value: str) -> str:
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

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
        """Run retrieval with strict ACL metadata filtering and citation sanitization."""
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
        expanded_document_ids = self._expand_document_id_candidates(scoped_document_ids)
        doc_filter = document_id_filter(expanded_document_ids)
        storage_paths = self._access_service.resolve_document_sources(scoped_document_ids)
        allowed_source_paths = self._build_allowed_source_paths(user, scoped_document_ids)
        allowed_source_paths = sorted(set(allowed_source_paths) | set(storage_paths))
        # Support both legacy metadata key (source_path) and actual vector metadata key (source).
        source_path_scope_filter = source_path_filter(allowed_source_paths) if allowed_source_paths else None
        source_scope_filter = source_filter(allowed_source_paths) if allowed_source_paths else None
        source_any_filter = any_metadata_filter(source_path_scope_filter, source_scope_filter)
        scope_filter = any_metadata_filter(doc_filter, source_any_filter)
        metadata_filter = combine_metadata_filters(department_filter, scope_filter)

        LOGGER.info(
            "RAG scope built user_id=%s departments=%s authorized_doc_count=%s requested_doc_count=%s "
            "source_path_allow_count=%s strict_scope=%s query=%r authorized_doc_ids=%s",
            user.user_id,
            effective_departments,
            len(scoped_document_ids),
            0 if requested_document_ids is None else len(requested_document_ids),
            len(allowed_source_paths),
            strict_document_scope,
            question,
            scoped_document_ids,
        )
        LOGGER.debug(
            "RAG metadata filter user_id=%s filter=%s",
            user.user_id,
            metadata_filter,
        )

        result = self._retrieval.query(
            question=question,
            mode=mode,
            strict_document_scope=strict_document_scope,
            metadata_filter=metadata_filter,
        )

        # Defense in depth: strip citations that are not part of authorized internal IDs.
        before_citations = len(result.get("citations", []))
        allowed = set(scoped_document_ids)
        allowed_expanded = set(self._expand_document_id_candidates(scoped_document_ids))
        allowed_compact = {self._compact_token(item) for item in allowed_expanded}
        safe_citations: list[Any] = []
        for citation in result.get("citations", []):
            if isinstance(citation, dict):
                document_label = str(citation.get("document", ""))
                citation_document_id = str(citation.get("document_id", "") or normalize_document_id(document_label))
                citation_candidates = set(self._expand_document_id_candidates([citation_document_id, document_label]))
                citation_compact = self._compact_token(citation_document_id or document_label)
                if citation_document_id in allowed or bool(citation_candidates & allowed_expanded) or any(token in citation_compact for token in allowed_compact):
                    safe_citations.append(citation)
                continue
            citation_text = str(citation)
            normalized_text = normalize_document_id(citation_text)
            if any(doc_id in citation_text for doc_id in allowed_expanded) or any(doc_id in normalized_text for doc_id in allowed_expanded):
                safe_citations.append(citation)
        result["citations"] = safe_citations
        LOGGER.info(
            "RAG result user_id=%s citations_before=%s citations_after=%s confidence=%s",
            user.user_id,
            before_citations,
            len(safe_citations),
            result.get("confidence", {}),
        )
        return result
