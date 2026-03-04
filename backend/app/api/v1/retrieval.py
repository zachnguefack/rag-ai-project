from fastapi import APIRouter, Depends

from app.api.deps import permission_dependency
from app.models.schema.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/search", response_model=RetrievalResponse)
def search(
    payload: RetrievalRequest,
    _: dict = Depends(permission_dependency("rag:query")),
    service: RetrievalService = Depends(RetrievalService),
) -> RetrievalResponse:
    return service.search(payload)
