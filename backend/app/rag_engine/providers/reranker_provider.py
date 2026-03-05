from __future__ import annotations


class NoopRerankerProvider:
    def rerank(self, items: list[dict]) -> list[dict]:
        return items
