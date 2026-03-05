from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_audit_service, get_rag_service, validate_api_key
from app.models.schema.chat import QueryRequest, QueryResponse
from app.models.schema.common import ErrorResponse
from app.services.audit_service import AuditService
from app.services.rag_service import RAGApplicationService

router = APIRouter(tags=["RAG Query"])


@router.post(
    '/chat/ask',
    response_model=QueryResponse,
    summary="Ask a RAG question (legacy)",
    description="Runs a question through the RAG service and returns the full response envelope.",
    responses={401: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def ask_question(
    request: QueryRequest,
    service: RAGApplicationService = Depends(get_rag_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> QueryResponse:
    result = service.answer(
        question=request.question,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
    )
    audit_service.record_query_event(
        user_id="anonymous",
        question=request.question,
        documents_retrieved=[str(citation) for citation in result.get("citations", [])],
        answer_generated=result.get("answer", ""),
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )
    return QueryResponse(**result)
