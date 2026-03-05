from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_rag_service, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.document import DocumentAccessResponse, IndexRequest, IndexResponse
from app.security.policies import Permission, RoleName
from app.security.rbac import require_permissions, require_roles
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService

router = APIRouter()


@router.post('/documents/index', response_model=IndexResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
@require_roles(
    RoleName.POWER_USER,
    RoleName.DOCUMENT_ADMINISTRATOR,
    RoleName.SYSTEM_ADMINISTRATOR,
    RoleName.SUPER_ADMINISTRATOR,
)
@require_permissions(Permission.INGEST_DOCUMENT)
def index_documents(request: IndexRequest, service: RAGApplicationService = Depends(get_rag_service)) -> IndexResponse:
    return IndexResponse(**service.run_indexing(force_reindex=request.force_reindex))


@router.get(
    '/documents/{document_id}/access',
    response_model=DocumentAccessResponse,
    dependencies=[Depends(validate_api_key)],
)
@require_permissions(Permission.READ_DOCUMENT)
def verify_document_access(
    document_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> DocumentAccessResponse:
    rbac_service.enforce_document_access(current_user, document_id)
    return DocumentAccessResponse(document_id=document_id, message="Access granted")
