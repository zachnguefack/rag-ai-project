from fastapi import APIRouter, Depends

from app.api.deps import permission_dependency
from app.models.schema.document import DocumentCreateRequest, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("", response_model=DocumentResponse)
def create_document(
    payload: DocumentCreateRequest,
    _: dict = Depends(permission_dependency("document:write")),
    service: DocumentService = Depends(DocumentService),
) -> DocumentResponse:
    return service.create_document(payload)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    _: dict = Depends(permission_dependency("document:read")),
    service: DocumentService = Depends(DocumentService),
) -> list[DocumentResponse]:
    return service.list_documents()
