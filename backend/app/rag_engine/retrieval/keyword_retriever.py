class KeywordRetriever:
    def retrieve(self, query: str, top_k: int) -> list[dict]:
        return [{"content": f"keyword match for {query}", "score": 0.7, "source": "keyword-index"}][:top_k]
