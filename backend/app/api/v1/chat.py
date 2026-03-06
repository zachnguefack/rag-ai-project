from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_audit_service, get_current_user, get_rag_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.chat import QueryRequest, QueryResponse
from app.models.schema.common import ErrorResponse
from app.services.audit_service import AuditService
from app.services.rag_service import RAGApplicationService

router = APIRouter(tags=["RAG Query"])


@router.post(
    '/chat/ask',
    response_model=QueryResponse,
    summary="Ask a RAG question (legacy)",
    description="Legacy endpoint now using secure document scope with user authorization checks.",
    responses={401: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def ask_question(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    service: RAGApplicationService = Depends(get_rag_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> QueryResponse:
    result = service.answer(
        user=user,
        question=request.question,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
    )
    audit_service.record_query_event(
        user_id=user.user_id,
        question=request.question,
        authorized_document_ids_count=int(result.get("authorized_document_ids_count", 0)),
        documents_retrieved=[str(citation) for citation in result.get("citations", [])],
        chunks_used=[str(citation) for citation in result.get("citations", [])],
        access_decision="allow" if result.get("citations") else "deny",
        strict_scope_blocked=not bool(result.get("citations")) and bool(request.strict_document_scope),
        answer_generated=result.get("answer", ""),
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )
    return QueryResponse(**result)
