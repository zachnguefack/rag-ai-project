class VectorRetriever:
    def retrieve(self, query: str, top_k: int) -> list[dict]:
        return [{"content": f"vector match for {query}", "score": 0.9, "source": "vector-db"}][:top_k]
