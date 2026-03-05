from __future__ import annotations

from rag_v2 import EmbeddingManager


class EmbeddingProvider:
    def __init__(self, manager: EmbeddingManager) -> None:
        self._manager = manager

    def embed_text(self, text: str):
        return self._manager.embed_texts([text])[0]
