from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Union

import chromadb
import numpy as np

LOGGER = logging.getLogger("rag_v2.store")
SimpleMeta = Dict[str, Union[str, int, float, bool]]


class VectorStore:
    """Persistent Chroma collection with stable IDs and sanitized metadata."""

    def __init__(self, collection_name: str = "rag_v2_docs", persist_directory: str = "data/vector_store", reset: bool = False):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)

        if reset:
            try:
                self.client.delete_collection(collection_name)
                LOGGER.info("Deleted collection=%s", collection_name)
            except Exception:
                LOGGER.info("Collection did not exist for reset: %s", collection_name)

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "RAG embeddings", "hnsw:space": "cosine"},
        )
        LOGGER.info("Collection ready name=%s count=%s", collection_name, self.collection.count())

    @staticmethod
    def _sanitize_metadata(md: Dict[str, Any]) -> SimpleMeta:
        out: SimpleMeta = {}
        for k, v in (md or {}).items():
            if v is None:
                continue
            out[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
        return out

    @staticmethod
    def _stable_chunk_id(source: str, page: int, chunk_index: int, content: str) -> str:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"{source}::p{page}::c{chunk_index}::{h}"

    def add_documents(self, documents: List[Any], embeddings: np.ndarray) -> None:
        if len(documents) != embeddings.shape[0]:
            raise ValueError("documents and embeddings lengths must match")

        ids: List[str] = []
        metadatas: List[SimpleMeta] = []
        docs_text: List[str] = []
        embs: List[List[float]] = []

        for i, doc in enumerate(documents):
            content = (getattr(doc, "page_content", "") or "").strip()
            if not content:
                continue

            md = dict(getattr(doc, "metadata", {}) or {})
            source = str(md.get("source") or "unknown_source")
            page = int(md.get("page") or 0)
            chunk_index = int(md.get("chunk_index") if md.get("chunk_index") is not None else i)
            doc_id = self._stable_chunk_id(source, page, chunk_index, content)

            clean_md = self._sanitize_metadata(md)
            clean_md.update({"source": source, "page": page, "chunk_index": chunk_index, "content_length": len(content)})

            ids.append(doc_id)
            metadatas.append(clean_md)
            docs_text.append(content)
            embs.append(embeddings[i].astype(np.float32).tolist())

        if not ids:
            LOGGER.warning("No non-empty chunks to upsert")
            return

        self.collection.upsert(ids=ids, embeddings=embs, metadatas=metadatas, documents=docs_text)
        LOGGER.info("Upsert complete chunks=%s total=%s", len(ids), self.collection.count())

    def delete_by_source(self, source: str) -> None:
        """Delete all chunks associated with a source file."""
        self.collection.delete(where={"source": source})
        LOGGER.info("Deleted chunks for source=%s", source)

    def reset_collection(self) -> None:
        """Delete all stored vectors in the current collection."""
        rows = self.collection.get(include=[])
        ids = rows.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
        LOGGER.info("Cleared collection=%s", self.collection_name)
