from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.v1.router import build_v1_router
from app.bootstrap.dev_rbac_seed import seed_dev_rbac_users
from app.config.settings import BackendSettings, load_settings
from app.security.middleware import RBACMiddleware
from app.services.auth_service import AuthService
from app.services.document_access_service import DocumentAccessService
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService
from app.services.scope_builder_service import ScopeBuilderService


logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "Authentication", "description": "User registration, login, logout, and identity endpoints."},
    {"name": "Users", "description": "Authenticated user profile and permission discovery."},
    {"name": "Documents", "description": "Document CRUD, access checks, versioning, and indexing workflows."},
    {"name": "RAG Query", "description": "Question-answering and retrieval endpoints powered by the RAG engine."},
    {"name": "Admin", "description": "Administrative endpoints requiring elevated privileges."},
    {"name": "Roles & Permissions", "description": "RBAC role, permission, and access validation management APIs."},
    {"name": "Audit", "description": "Audit trail endpoints for traceability and compliance."},
    {"name": "System", "description": "Operational and health endpoints for runtime monitoring."},
]


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    app = FastAPI(
        title=runtime_settings.app_name,
        description=(
            "Enterprise RAG backend API for secure authentication, document lifecycle management, "
            "retrieval-augmented generation, and auditability.\n\n"
            "Authentication options in Swagger: use `Authorization: Bearer <token>` or set `X-User-Id` "
            "for local/dev identity simulation consumed by RBAC resolution."
        ),
        version=runtime_settings.app_version,
        contact={"name": "Backend Platform Team", "email": "backend-team@example.com"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=OPENAPI_TAGS,
    )

    document_access_service = DocumentAccessService()
    scope_builder_service = ScopeBuilderService(document_access_service=document_access_service)
    service = RAGApplicationService(runtime_settings, scope_builder=scope_builder_service)
    rbac_service = RBACService()
    auth_service = AuthService(settings=runtime_settings)

    def service_dependency() -> RAGApplicationService:
        return service

    def settings_dependency() -> BackendSettings:
        return runtime_settings

    def rbac_dependency() -> RBACService:
        return rbac_service

    def auth_dependency() -> AuthService:
        return auth_service

    app.dependency_overrides[RAGApplicationService] = service_dependency
    app.dependency_overrides[BackendSettings] = settings_dependency
    app.dependency_overrides[RBACService] = rbac_dependency
    app.dependency_overrides[AuthService] = auth_dependency

    def init_database() -> None:
        logger.info("[STARTUP] Initializing database session metadata")

    @app.on_event("startup")
    def startup_event() -> None:
        init_database()
        seed_dev_rbac_users(settings=runtime_settings, rbac_service=rbac_service)
        logger.info("[STARTUP] Application startup completed")

    app.add_middleware(RBACMiddleware, rbac_service=rbac_service, auth_service=auth_service)
    app.include_router(build_v1_router(), prefix='/api/v1')
    return app


app = create_app()
