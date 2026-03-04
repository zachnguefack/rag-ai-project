from fastapi import APIRouter, Depends

from app.api.deps import permission_dependency
from app.models.schema.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
def ask(
    payload: ChatRequest,
    user: dict = Depends(permission_dependency("rag:query")),
    service: RAGService = Depends(RAGService),
) -> ChatResponse:
    return service.answer(payload, user)
