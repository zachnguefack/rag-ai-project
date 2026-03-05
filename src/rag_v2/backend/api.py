from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from .access_control import UserContext
from .schemas import HealthResponse, IndexRequest, IndexResponse, QueryRequest, QueryResponse
from .services import RAGApplicationService
from .settings import BackendSettings

_ALLOWED_QUERY_ROLES = {
    "standard_user",
    "power_user",
    "document_administrator",
    "compliance_officer",
    "system_administrator",
    "super_administrator",
}


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

    def resolve_user_context(
        x_user_id: str | None = Header(default=None),
        x_user_role: str | None = Header(default=None),
    ) -> UserContext:
        if not x_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-Id header.")

        role = (x_user_role or "standard_user").strip().lower()
        if role not in _ALLOWED_QUERY_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unsupported role '{x_user_role}'.",
            )
        return UserContext(user_id=x_user_id.strip(), role=role)

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service=settings.app_name, version=settings.app_version)

    @router.post("/index", response_model=IndexResponse, dependencies=[Depends(validate_api_key)])
    def index_documents(request: IndexRequest) -> IndexResponse:
        return IndexResponse(**service.run_indexing(force_reindex=request.force_reindex))

    @router.post("/query", response_model=QueryResponse, dependencies=[Depends(validate_api_key)])
    def query(request: QueryRequest, user: UserContext = Depends(resolve_user_context)) -> QueryResponse:
        result = service.answer(
            question=request.question,
            mode=request.mode,
            user=user,
            strict_document_scope=request.strict_document_scope,
        )
        return QueryResponse(**result)

    return router
