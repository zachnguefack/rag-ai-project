from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_rag_service, validate_api_key
from app.models.schema.chat import QueryRequest, QueryResponse
from app.services.rag_service import RAGApplicationService

router = APIRouter()


@router.post('/chat/ask', response_model=QueryResponse, dependencies=[Depends(validate_api_key)])
def ask_question(request: QueryRequest, service: RAGApplicationService = Depends(get_rag_service)) -> QueryResponse:
    result = service.answer(
        question=request.question,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
    )
    return QueryResponse(**result)
