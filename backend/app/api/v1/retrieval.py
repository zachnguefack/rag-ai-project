from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_audit_service,
    get_current_user,
    get_rbac_service,
    get_secure_retriever,
    validate_api_key,
)
from app.models.domain.user import User
from app.models.schema.common import ErrorResponse
from app.models.schema.retrieval import RAGQueryRequest, RAGQueryResponse
from app.security.policies import Permission
from app.services.audit_service import AuditService
from app.services.rbac_service import RBACService
from app.services.secure_retriever import SecureRetriever

router = APIRouter(tags=["RAG Query"])


@router.post(
    '/rag/query',
    response_model=RAGQueryResponse,
    summary="Query enterprise knowledge base",
    description=(
        "Answers a question using authorization-aware retrieval. The backend computes query scope as "
        "(department documents + explicit document grants - revoked grants) based on the authenticated user. "
        "Normal users are never allowed to query outside this scope. Admin-equivalent users can query broader "
        "scope only when their role grants department/document access through the same RBAC model."
    ),
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    dependencies=[Depends(validate_api_key)],
)
def rag_query(
    request: RAGQueryRequest,
    user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    secure_retriever: SecureRetriever = Depends(get_secure_retriever),
    audit_service: AuditService = Depends(get_audit_service),
) -> RAGQueryResponse:
    rbac_service.enforce_permission(user, Permission.SEARCH_DOCUMENT)
    rbac_service.enforce_permission(user, Permission.READ_DOCUMENT)

    result = secure_retriever.retrieve(
        question=request.question,
        user=user,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
        department_id=request.department_id,
        document_ids=request.document_ids,
    )

    audit_service.record_query_event(
        user_id=user.user_id,
        question=request.question,
        documents_retrieved=[str(citation) for citation in result.get("citations", [])],
        answer_generated=result.get("answer", ""),
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )

    return RAGQueryResponse(
        answer=result["answer"],
        citations=[str(citation) for citation in result.get("citations", [])],
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )
