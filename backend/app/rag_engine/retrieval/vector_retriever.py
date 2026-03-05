from __future__ import annotations

from rag_v2 import RAGRetriever


class VectorRetriever:
    def __init__(self, retriever: RAGRetriever) -> None:
        self._retriever = retriever
