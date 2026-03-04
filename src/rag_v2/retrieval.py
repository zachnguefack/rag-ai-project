from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .embeddings import EmbeddingManager
from .store import VectorStore


class RAGRetriever:
    def __init__(self, vector_store: VectorStore, embedding_manager: EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    @staticmethod
    def _normalize_where(where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not where:
            return None
        if any(str(k).startswith("$") for k in where.keys()) or len(where) == 1:
            return where
        return {"$and": [{k: v} for k, v in where.items()]}

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        qvec = self.embedding_manager.embed_query(query).astype(np.float32).tolist()
        rows = self.vector_store.collection.query(
            query_embeddings=[qvec],
            n_results=max(top_k, 1),
            where=self._normalize_where(metadata_filter),
        )

        docs = rows.get("documents", [[]])[0]
        metas = rows.get("metadatas", [[]])[0]
        dists = rows.get("distances", [[]])[0]
        ids = rows.get("ids", [[]])[0]

        output: List[Dict[str, Any]] = []
        for rank, (doc_id, content, md, dist) in enumerate(zip(ids, docs, metas, dists), start=1):
            distance = float(dist)
            similarity = float(np.clip(1.0 - distance, 0.0, 1.0))
            if similarity < score_threshold:
                continue
            output.append(
                {
                    "id": doc_id,
                    "content": content,
                    "metadata": md or {},
                    "distance": round(distance, 6),
                    "similarity_score": round(similarity, 6),
                    "rank": rank,
                }
            )

        output.sort(key=lambda x: x["similarity_score"], reverse=True)
        return output
