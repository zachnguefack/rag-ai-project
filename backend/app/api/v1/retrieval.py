from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_document_repository, get_rag_service, get_rbac_service
from app.database.repositories.document_repo import DocumentRepository
from app.models.domain.user import User
from app.models.schema.retrieval import RAGQueryRequest, RAGQueryResponse
from app.security.policies import DOCUMENT_GLOBAL_ACCESS_ROLES, Permission
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService

router = APIRouter()


def _is_document_accessible(user: User, document_id: str, owner_user_id: str, allowed_users: set[str], allowed_roles: set[str]) -> bool:
    if user.role_names & DOCUMENT_GLOBAL_ACCESS_ROLES:
        return True
    if owner_user_id == user.user_id:
        return True
    if user.user_id in allowed_users or document_id in user.document_allow_list:
        return True

    user_roles = {role.value for role in user.role_names}
    if user_roles & allowed_roles:
        return True
    return False


def _build_accessible_document_ids(user: User, document_repository: DocumentRepository) -> list[str]:
    docs = document_repository.list()
    accessible_doc_ids: list[str] = []

    for doc in docs:
        if _is_document_accessible(
            user=user,
            document_id=doc.document_id,
            owner_user_id=doc.owner_user_id,
            allowed_users=set(doc.allowed_users),
            allowed_roles=set(doc.allowed_roles),
        ):
            accessible_doc_ids.append(doc.document_id)

    return accessible_doc_ids


@router.post('/rag/query', response_model=RAGQueryResponse)
def rag_query(
    request: RAGQueryRequest,
    user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
    document_repository: DocumentRepository = Depends(get_document_repository),
    rag_service: RAGApplicationService = Depends(get_rag_service),
) -> RAGQueryResponse:
    rbac_service.enforce_permission(user, Permission.SEARCH_DOCUMENT)
    rbac_service.enforce_permission(user, Permission.READ_DOCUMENT)

    accessible_doc_ids = _build_accessible_document_ids(user=user, document_repository=document_repository)

    metadata_filter = None
    if accessible_doc_ids:
        metadata_filter = {"document_id": {"$in": accessible_doc_ids}}

    result = rag_service.answer(
        question=request.question,
        mode=request.mode,
        strict_document_scope=request.strict_document_scope,
        metadata_filter=metadata_filter,
    )

    return RAGQueryResponse(
        answer=result["answer"],
        citations=[str(citation) for citation in result.get("citations", [])],
        confidence_score=float(result.get("confidence", {}).get("score", 0.0)),
    )
