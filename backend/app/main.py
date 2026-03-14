from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import build_v1_router
from app.bootstrap.dev_rbac_seed import seed_dev_rbac_users
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.database.sqlite import SQLiteStore
from app.bootstrap.dev_seed_dataset import seed_dev_dataset
from app.config.settings import BackendSettings, load_settings
from app.security.middleware import RBACMiddleware
from app.services.auth_service import AuthService
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService

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
            "for local/dev identity simulation consumed by RBAC resolution.\n\n"
            "Access model: each user has one primary department and each document belongs to one primary "
            "department. Effective retrieval scope is computed before retrieval as: department documents + "
            "explicit user document grants - revoked grants. Query endpoints (`/api/v1/rag/query` and legacy "
            "`/api/v1/chat/ask`) enforce this scope server-side. `document_id` is an internal identifier, not "
            "a filesystem path."
        ),
        version=runtime_settings.app_version,
        contact={"name": "Backend Platform Team", "email": "backend-team@example.com"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=OPENAPI_TAGS,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = SQLiteStore(runtime_settings.metadata_db_path)
    user_repository = UserRepository(store)
    document_repository = DocumentRepository(store)
    user_document_access_repository = UserDocumentAccessRepository(store)
    user_department_access_repository = UserDepartmentAccessRepository(store)

    service = RAGApplicationService(runtime_settings)
    rbac_service = RBACService(
        user_repository=user_repository,
        document_repository=document_repository,
        user_document_access_repository=user_document_access_repository,
        user_department_access_repository=user_department_access_repository,
    )
    auth_service = AuthService(
        settings=runtime_settings,
        user_repository=user_repository,
        user_department_access_repository=user_department_access_repository,
    )

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
        seed_dev_dataset(settings=runtime_settings)
        logger.info("[STARTUP] Application startup completed")

    allow_header_identity = runtime_settings.allow_unauthenticated or runtime_settings.app_env.lower() in {"development", "dev", "local", "test"}
    app.add_middleware(
        RBACMiddleware,
        rbac_service=rbac_service,
        auth_service=auth_service,
        allow_header_identity=allow_header_identity,
    )
    app.include_router(build_v1_router(), prefix='/api/v1')
    return app


app = create_app()