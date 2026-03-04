from app.models.schema.retrieval import RetrievalRequest, RetrievalResponse
from app.rag_engine.retrieval.hybrid import HybridRetriever


class RetrievalService:
    def __init__(self) -> None:
        self.hybrid = HybridRetriever()

    def search(self, payload: RetrievalRequest) -> RetrievalResponse:
        results = self.hybrid.retrieve(payload.query, payload.top_k)
        return RetrievalResponse(results=results)
