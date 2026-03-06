from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_audit_service, get_current_user, get_rbac_service, get_retrieval_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.common import ErrorResponse
from app.models.schema.retrieval import RAGQueryRequest, RAGQueryResponse
from app.security.policies import Permission
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["RAG Query"])


@router.post(
    '/rag/query',
    response_model=RAGQueryResponse,
    summary="Query enterprise knowledge base",
    description=(
        "Secure document-scoped retrieval. The service computes authorized document scope before retrieval, "
        "filters retrieval by internal document IDs, validates strict scope evidence, and only then calls the LLM."
    ),
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def rag_query(
    request: RAGQueryRequest,
    user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> RAGQueryResponse:
    rbac_service.enforce_permission(user, Permission.SEARCH_DOCUMENT)
    rbac_service.enforce_permission(user, Permission.READ_DOCUMENT)

    result = retrieval_service.query(
        user=user,
        question=request.question,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
        metadata_filter=None,
    )
    strict_scope_blocked = not bool(result.get("citations")) and request.strict_document_scope is True

    audit_service.record_query_event(
        user_id=user.user_id,
        question=request.question,
        authorized_document_ids_count=int(result.get("authorized_document_ids_count", 0)),
        documents_retrieved=[str(citation) for citation in result.get("citations", [])],
        chunks_used=[str(citation) for citation in result.get("citations", [])],
        access_decision="allow" if result.get("citations") else "deny",
        strict_scope_blocked=strict_scope_blocked,
        answer_generated=result.get("answer", ""),
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )

    return RAGQueryResponse(
        answer=result["answer"],
        citations=[str(citation) for citation in result.get("citations", [])],
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
        authorized_document_ids_count=int(result.get("authorized_document_ids_count", 0)),
        strict_scope_blocked=strict_scope_blocked,
    )
