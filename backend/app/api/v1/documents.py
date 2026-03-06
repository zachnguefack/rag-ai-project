from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_document_service, get_ingestion_service, get_rbac_service, validate_api_key
from app.models.domain.user import User
from app.models.schema.common import ErrorResponse
from app.models.schema.document import (
    DocumentAccessResponse,
    DocumentCreateRequest,
    DocumentDeleteResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionResponse,
    IndexRequest,
    IndexResponse,
)
from app.security.policies import Permission, RoleName
from app.security.rbac import require_permissions, require_roles
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.rbac_service import RBACService

router = APIRouter(tags=["Documents"])


@router.post('/documents/index', response_model=IndexResponse, summary="Run document indexing", dependencies=[Depends(validate_api_key), Depends(get_current_user)])
@require_roles(RoleName.POWER_USER, RoleName.DOCUMENT_ADMINISTRATOR, RoleName.SYSTEM_ADMINISTRATOR, RoleName.SUPER_ADMINISTRATOR)
@require_permissions(Permission.INGEST_DOCUMENT)
def index_documents(request: IndexRequest, service: IngestionService = Depends(get_ingestion_service)) -> IndexResponse:
    job = service.run_incremental_indexing(force_reindex=request.force_reindex)
    return IndexResponse(indexed_files=job.indexed_files, indexed_chunks=job.indexed_chunks, removed_files=job.removed_files, reused_existing_index=job.reused_existing_index)


@router.get('/documents/{document_id}/access', response_model=DocumentAccessResponse, dependencies=[Depends(validate_api_key)])
@require_permissions(Permission.READ_DOCUMENT)
def verify_document_access(document_id: str, current_user: User = Depends(get_current_user), rbac_service: RBACService = Depends(get_rbac_service)) -> DocumentAccessResponse:
    rbac_service.enforce_document_access(current_user, document_id)
    return DocumentAccessResponse(document_id=document_id, message="Access granted")


@router.post('/documents', response_model=DocumentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def upload_document(request: DocumentCreateRequest, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    return document_service.create_document(current_user, request)


@router.get('/documents', response_model=list[DocumentResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def list_documents(current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> list[DocumentResponse]:
    return document_service.list_documents(current_user)


@router.get('/documents/search', response_model=list[DocumentResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def search_documents(
    q: str = Query(default="", description="Case-insensitive title contains filter."),
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    docs = document_service.list_documents(current_user)
    term = q.lower().strip()
    if not term:
        return docs
    return [d for d in docs if term in d.title.lower()]


@router.get('/documents/{document_id}/metadata', response_model=DocumentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def get_document_metadata(document_id: str, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    return document_service.get_document(current_user, document_id)


@router.get('/documents/{document_id}', response_model=DocumentResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}}, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def get_document(document_id: str, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    return document_service.get_document(current_user, document_id)


@router.put('/documents/{document_id}', response_model=DocumentResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def update_document(document_id: str, request: DocumentUpdateRequest, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    return document_service.update_document(current_user, document_id, request)


@router.delete('/documents/{document_id}', response_model=DocumentDeleteResponse, dependencies=[Depends(validate_api_key), Depends(get_current_user)])
def delete_document(document_id: str, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> DocumentDeleteResponse:
    return document_service.delete_document(current_user, document_id)


@router.get('/documents/{document_id}/versions', response_model=list[DocumentVersionResponse], dependencies=[Depends(validate_api_key), Depends(get_current_user)])
@require_permissions(Permission.READ_DOCUMENT)
def list_document_versions(document_id: str, current_user: User = Depends(get_current_user), document_service: DocumentService = Depends(get_document_service)) -> list[DocumentVersionResponse]:
    return document_service.list_document_versions(current_user, document_id)
