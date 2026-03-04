from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from .store import VectorStore
from .embeddings import EmbeddingManager


class RAGRetriever:
    def __init__(self, vector_store: VectorStore, embedding_manager: EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    @staticmethod
    def _clean_query(query: str) -> str:
        return (query or "").strip()

    @staticmethod
    def _normalize_where(where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not where:
            return None
        if any(str(k).startswith("$") for k in where.keys()):
            return where
        if len(where) == 1:
            return where
        return {"$and": [{k: v} for k, v in where.items()]}

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:

        query = self._clean_query(query)
        if not query:
            return []

        where = self._normalize_where(metadata_filter)
        qvec = self.embedding_manager.embed_query(query).astype(np.float32).tolist()

        results = self.vector_store.collection.query(
            query_embeddings=[qvec],
            n_results=top_k,
            where=where,
        )

        docs = results.get("documents", [[]])[0] if results else []
        metas = results.get("metadatas", [[]])[0] if results else []
        dists = results.get("distances", [[]])[0] if results else []
        ids = results.get("ids", [[]])[0] if results else []

        if not docs:
            return []

        out: List[Dict[str, Any]] = []
        for rank, (doc_id, content, md, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
            dist_f = float(dist)
            sim = 1.0 - dist_f  # cosine
            if sim >= score_threshold:
                out.append(
                    {
                        "id": doc_id,
                        "content": content,
                        "metadata": md,
                        "similarity_score": round(sim, 4),
                        "distance": round(dist_f, 4),
                        "rank": rank,
                    }
                )

        out.sort(key=lambda x: x["similarity_score"], reverse=True)
        return out