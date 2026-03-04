from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from langchain_core.documents import Document

from .embeddings import EmbeddingManager
from .store import VectorStore
from .text import split_documents

LOGGER = logging.getLogger("rag_v2.indexing")


@dataclass(slots=True)
class IndexingConfig:
    chunk_size: int = 900
    chunk_overlap: int = 140


def index_documents(
    documents: Iterable[Document],
    embedding_manager: EmbeddingManager,
    vector_store: VectorStore,
    cfg: IndexingConfig | None = None,
) -> int:
    cfg = cfg or IndexingConfig()

    chunks = split_documents(documents, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)
    if not chunks:
        LOGGER.warning("No chunks produced from ingestion.")
        return 0

    texts = [c.page_content for c in chunks]
    vectors = embedding_manager.embed_documents(texts)
    vector_store.add_documents(chunks, vectors)
    LOGGER.info("Indexed chunks=%s", len(chunks))
    return len(chunks)


# Backward-compatible API
EmbeddingConfig = IndexingConfig

def embed_and_store_chunks(chunks, embedding_manager, vectorstore, cfg=None):
    cfg = cfg or IndexingConfig()
    return index_documents(chunks, embedding_manager, vectorstore, cfg=cfg)
