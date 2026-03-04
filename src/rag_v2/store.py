from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Union

import chromadb
import numpy as np

SimpleMeta = Dict[str, Union[str, int, float, bool]]


class VectorStore:
    """Persistent ChromaDB collection with robust indexing."""

    def __init__(
        self,
        collection_name: str = "rag_v2_docs",
        persist_directory: str = "data/vector_store",
        reset: bool = False,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.reset = reset

        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        if self.reset:
            try:
                self.client.delete_collection(self.collection_name)
                print(f"[VectorStore] Deleted collection: {self.collection_name}")
            except Exception:
                pass

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Document embeddings for RAG",
                "hnsw:space": "cosine",
            },
        )

        print(f"[VectorStore] Collection={self.collection_name} | count={self.collection.count()}")

    @staticmethod
    def _sanitize_metadata(md: Dict[str, Any]) -> SimpleMeta:
        clean: SimpleMeta = {}
        for k, v in (md or {}).items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean

    @staticmethod
    def _normalize_source(md: Dict[str, Any]) -> str:
        src = md.get("source") or md.get("file_path") or md.get("path") or "unknown_source"
        return str(src)

    @staticmethod
    def _stable_chunk_id(source: str, page: int, chunk_index: int, content: str) -> str:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"{source}::p{page}::c{chunk_index}::{h}"

    def add_documents(self, documents: List[Any], embeddings: np.ndarray) -> None:
        if not documents:
            print("[VectorStore] No documents provided.")
            return
        if not isinstance(embeddings, np.ndarray) or embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2D numpy array: (n_docs, dim)")
        if len(documents) != embeddings.shape[0]:
            raise ValueError("Number of documents must match number of embeddings")

        ids: List[str] = []
        metadatas: List[SimpleMeta] = []
        docs_text: List[str] = []
        embs_list: List[List[float]] = embeddings.astype(np.float32).tolist()

        for i, doc in enumerate(documents):
            md_raw = getattr(doc, "metadata", {}) or {}
            content = (getattr(doc, "page_content", "") or "").strip()
            if not content:
                continue

            source = self._normalize_source(md_raw)
            page = int(md_raw.get("page") or 0)
            chunk_index = int(md_raw.get("chunk_index") if md_raw.get("chunk_index") is not None else i)

            doc_id = self._stable_chunk_id(source, page, chunk_index, content)

            md = self._sanitize_metadata(md_raw)
            md["source"] = source
            md["page"] = page
            md["chunk_index"] = chunk_index
            md["content_length"] = len(content)

            ids.append(doc_id)
            metadatas.append(md)
            docs_text.append(content)

        if not ids:
            print("[VectorStore] Nothing to upsert.")
            return

        self.collection.upsert(
            ids=ids,
            embeddings=embs_list,
            metadatas=metadatas,
            documents=docs_text,
        )

        print(f"[VectorStore] Upserted {len(ids)} chunks | new count={self.collection.count()}")