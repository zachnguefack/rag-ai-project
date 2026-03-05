from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_rag_service, validate_api_key
from app.models.schema.document import IndexRequest, IndexResponse
from app.services.rag_service import RAGApplicationService

router = APIRouter()


@router.post('/documents/index', response_model=IndexResponse, dependencies=[Depends(validate_api_key)])
def index_documents(request: IndexRequest, service: RAGApplicationService = Depends(get_rag_service)) -> IndexResponse:
    return IndexResponse(**service.run_indexing(force_reindex=request.force_reindex))
