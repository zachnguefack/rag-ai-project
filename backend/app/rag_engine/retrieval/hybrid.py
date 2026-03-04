from app.rag_engine.retrieval.keyword_retriever import KeywordRetriever
from app.rag_engine.retrieval.vector_retriever import VectorRetriever


class HybridRetriever:
    def __init__(self) -> None:
        self.vector = VectorRetriever()
        self.keyword = KeywordRetriever()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        combined = self.vector.retrieve(query, top_k) + self.keyword.retrieve(query, top_k)
        combined.sort(key=lambda item: item["score"], reverse=True)
        return combined[:top_k]
