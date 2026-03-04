from app.models.schema.chat import ChatRequest, ChatResponse
from app.observability.audit import emit_audit_event
from app.rag_engine.generation.answer_builder import AnswerBuilder
from app.rag_engine.retrieval.hybrid import HybridRetriever


class RAGService:
    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.answer_builder = AnswerBuilder()

    def answer(self, payload: ChatRequest, user: dict) -> ChatResponse:
        chunks = self.retriever.retrieve(payload.question, payload.top_k)
        answer = self.answer_builder.build(payload.question, chunks)
        emit_audit_event("rag.query", user.get("sub", "anonymous"), {"question": payload.question})
        return ChatResponse(answer=answer, citations=[r["source"] for r in chunks])
