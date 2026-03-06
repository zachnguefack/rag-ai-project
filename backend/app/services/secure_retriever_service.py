from __future__ import annotations

from typing import Any

from rag_v2 import EmbeddingManager, RAGRetriever, VectorStore

from app.models.domain.user import User
from app.rag_engine.retrieval.filters import document_id_filter
from app.services.scope_builder_service import ScopeBuilderService


class SecureRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_manager: EmbeddingManager,
        scope_builder: ScopeBuilderService,
    ) -> None:
        self._vector_store = vector_store
        self._retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedding_manager)
        self._scope_builder = scope_builder

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        metadata_filter: dict[str, Any] | None = None,
        user: User | None = None,
    ) -> list[dict[str, Any]]:
        if user is None:
            return []

        scope = self._scope_builder.build_scope(user)
        authorized_ids = scope.authorized_document_ids
        if not authorized_ids:
            return []

        secure_filter = document_id_filter(authorized_ids)
        if metadata_filter:
            secure_filter = {"$and": [secure_filter, metadata_filter]}

        vector_hits = self._retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=secure_filter,
        )
        keyword_hits = self._keyword_search(question=query, allowed_document_ids=authorized_ids, top_k=top_k)
        merged = self._merge(vector_hits=vector_hits, keyword_hits=keyword_hits)

        allowed = set(authorized_ids)
        filtered = [h for h in merged if h.get("metadata", {}).get("document_id") in allowed]
        return filtered

    def _keyword_search(self, *, question: str, allowed_document_ids: list[str], top_k: int) -> list[dict[str, Any]]:
        if not question.strip():
            return []
        query_terms = {term.lower() for term in question.split() if len(term) > 2}
        if not query_terms:
            return []

        rows = self._vector_store.collection.get(where=document_id_filter(allowed_document_ids), include=["metadatas", "documents"])
        docs = rows.get("documents", [])
        metas = rows.get("metadatas", [])
        ids = rows.get("ids", [])
        hits: list[dict[str, Any]] = []
        for cid, text, md in zip(ids, docs, metas):
            text_l = (text or "").lower()
            overlap = sum(1 for term in query_terms if term in text_l)
            if overlap == 0:
                continue
            hits.append(
                {
                    "id": cid,
                    "content": text,
                    "metadata": md or {},
                    "distance": round(1 - min(overlap / max(len(query_terms), 1), 1), 6),
                    "similarity_score": round(min(overlap / max(len(query_terms), 1), 1), 6),
                    "rank": 0,
                }
            )
        hits.sort(key=lambda x: x["similarity_score"], reverse=True)
        return hits[:top_k]

    @staticmethod
    def _merge(*, vector_hits: list[dict[str, Any]], keyword_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for hit in vector_hits + keyword_hits:
            key = str(hit.get("id"))
            if key not in merged or hit.get("similarity_score", 0) > merged[key].get("similarity_score", 0):
                merged[key] = hit
        out = list(merged.values())
        out.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        return out
