from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from .schemas import HealthResponse, IndexRequest, IndexResponse, QueryRequest, QueryResponse
from .services import RAGApplicationService
from .settings import BackendSettings


def build_router(service: RAGApplicationService, settings: BackendSettings) -> APIRouter:
    router = APIRouter()

    def validate_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if settings.allow_unauthenticated:
            return
        if not settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server API key is not configured.",
            )
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service=settings.app_name, version=settings.app_version)

    @router.post("/index", response_model=IndexResponse, dependencies=[Depends(validate_api_key)])
    def index_documents(request: IndexRequest) -> IndexResponse:
        return IndexResponse(**service.run_indexing(force_reindex=request.force_reindex))

    @router.post("/query", response_model=QueryResponse, dependencies=[Depends(validate_api_key)])
    def query(request: QueryRequest) -> QueryResponse:
        result = service.answer(
            question=request.question,
            mode=request.mode,
            strict_document_scope=request.strict_document_scope,
        )
        return QueryResponse(**result)

    return router
