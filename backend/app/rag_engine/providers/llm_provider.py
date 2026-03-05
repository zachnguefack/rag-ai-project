from __future__ import annotations

from rag_v2.answer import RAGService


class LLMProvider:
    def __init__(self, service: RAGService) -> None:
        self._service = service

    @property
    def service(self) -> RAGService:
        return self._service
