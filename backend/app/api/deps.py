from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config.settings import BackendSettings, load_settings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.ingest_job_repo import IngestJobRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.models.domain.user import User
from app.security.oauth2 import bearer_scheme
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.department_service import DepartmentService
from app.services.document_access_service import DocumentAccessService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGApplicationService
from app.services.rbac_service import RBACService
from app.services.retrieval_service import RetrievalService
from app.services.scope_builder_service import ScopeBuilderService
from app.services.secure_retriever import SecureRetriever

_runtime_settings: BackendSettings | None = None
_runtime_service: RAGApplicationService | None = None
_runtime_rbac: RBACService | None = None
_runtime_auth: AuthService | None = None
_runtime_document_repo: DocumentRepository | None = None
_runtime_department_repo: DepartmentRepository | None = None
_runtime_user_repo: UserRepository | None = None
_runtime_user_document_access_repo: UserDocumentAccessRepository | None = None
_runtime_scope_builder: ScopeBuilderService | None = None
_runtime_document_access_service: DocumentAccessService | None = None
_runtime_department_service: DepartmentService | None = None
_runtime_document_service: DocumentService | None = None
_runtime_audit_service: AuditService | None = None
_runtime_retrieval_service: RetrievalService | None = None
_runtime_secure_retriever: SecureRetriever | None = None
_runtime_ingestion_service: IngestionService | None = None
_runtime_ingest_job_repo: IngestJobRepository | None = None

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
x_user_id_header = APIKeyHeader(name="X-User-Id", auto_error=False, description="Local/dev identity header consumed by RBAC resolution.")


def get_settings() -> BackendSettings:
    global _runtime_settings
    if _runtime_settings is None:
        _runtime_settings = load_settings()
    return _runtime_settings


def get_document_repository() -> DocumentRepository:
    global _runtime_document_repo
    if _runtime_document_repo is None:
        _runtime_document_repo = DocumentRepository()
    return _runtime_document_repo


def get_user_repository() -> UserRepository:
    global _runtime_user_repo
    if _runtime_user_repo is None:
        _runtime_user_repo = UserRepository()
    return _runtime_user_repo


def get_department_repository() -> DepartmentRepository:
    global _runtime_department_repo
    if _runtime_department_repo is None:
        _runtime_department_repo = DepartmentRepository()
    return _runtime_department_repo


def get_user_document_access_repository() -> UserDocumentAccessRepository:
    global _runtime_user_document_access_repo
    if _runtime_user_document_access_repo is None:
        _runtime_user_document_access_repo = UserDocumentAccessRepository()
    return _runtime_user_document_access_repo


def get_scope_builder_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    user_document_access_repository: UserDocumentAccessRepository = Depends(get_user_document_access_repository),
) -> ScopeBuilderService:
    global _runtime_scope_builder
    if _runtime_scope_builder is None:
        _runtime_scope_builder = ScopeBuilderService(document_repository, user_document_access_repository)
    return _runtime_scope_builder


def get_ingest_job_repository() -> IngestJobRepository:
    global _runtime_ingest_job_repo
    if _runtime_ingest_job_repo is None:
        _runtime_ingest_job_repo = IngestJobRepository()
    return _runtime_ingest_job_repo


def get_rag_service(settings: BackendSettings = Depends(get_settings)) -> RAGApplicationService:
    global _runtime_service
    if _runtime_service is None:
        _runtime_service = RAGApplicationService(settings)
    return _runtime_service


def get_retrieval_service(rag_service: RAGApplicationService = Depends(get_rag_service)) -> RetrievalService:
    global _runtime_retrieval_service
    if _runtime_retrieval_service is None:
        _runtime_retrieval_service = RetrievalService(rag_service)
    return _runtime_retrieval_service


def get_ingestion_service(
    rag_service: RAGApplicationService = Depends(get_rag_service),
    ingest_job_repository: IngestJobRepository = Depends(get_ingest_job_repository),
) -> IngestionService:
    global _runtime_ingestion_service
    if _runtime_ingestion_service is None:
        _runtime_ingestion_service = IngestionService(rag_service=rag_service, ingest_job_repo=ingest_job_repository)
    return _runtime_ingestion_service


def get_rbac_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    user_document_access_repository: UserDocumentAccessRepository = Depends(get_user_document_access_repository),
) -> RBACService:
    global _runtime_rbac
    if _runtime_rbac is None:
        _runtime_rbac = RBACService(
            document_repository=document_repository,
            user_repository=user_repository,
            user_document_access_repository=user_document_access_repository,
        )
    return _runtime_rbac


def get_document_access_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    user_document_access_repository: UserDocumentAccessRepository = Depends(get_user_document_access_repository),
    scope_builder_service: ScopeBuilderService = Depends(get_scope_builder_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> DocumentAccessService:
    global _runtime_document_access_service
    if _runtime_document_access_service is None:
        _runtime_document_access_service = DocumentAccessService(
            document_repository=document_repository,
            user_document_access_repository=user_document_access_repository,
            scope_builder=scope_builder_service,
            rbac_service=rbac_service,
        )
    return _runtime_document_access_service


def get_secure_retriever(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    document_access_service: DocumentAccessService = Depends(get_document_access_service),
) -> SecureRetriever:
    global _runtime_secure_retriever
    if _runtime_secure_retriever is None:
        _runtime_secure_retriever = SecureRetriever(retrieval_service, document_access_service)
    return _runtime_secure_retriever


def get_department_service(
    department_repository: DepartmentRepository = Depends(get_department_repository),
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DepartmentService:
    global _runtime_department_service
    if _runtime_department_service is None:
        _runtime_department_service = DepartmentService(department_repository, document_repository)
    return _runtime_department_service


def get_audit_service() -> AuditService:
    global _runtime_audit_service
    if _runtime_audit_service is None:
        _runtime_audit_service = AuditService()
    return _runtime_audit_service


def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    rbac_service: RBACService = Depends(get_rbac_service),
    document_access_service: DocumentAccessService = Depends(get_document_access_service),
    user_document_access_repository: UserDocumentAccessRepository = Depends(get_user_document_access_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> DocumentService:
    global _runtime_document_service
    if _runtime_document_service is None:
        _runtime_document_service = DocumentService(
            document_repository,
            rbac_service,
            document_access_service,
            user_document_access_repository,
            audit_service,
        )
    return _runtime_document_service


def get_auth_service(settings: BackendSettings = Depends(get_settings)) -> AuthService:
    global _runtime_auth
    if _runtime_auth is None:
        _runtime_auth = AuthService(settings=settings)
    return _runtime_auth


def validate_api_key(x_api_key: str | None = Security(api_key_header), settings: BackendSettings = Depends(get_settings)) -> None:
    if settings.allow_unauthenticated:
        return
    if not settings.api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server API key is not configured.")
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")


def get_current_user(
    request: Request,
    x_user_id: str | None = Security(x_user_id_header),
    credentials=Security(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> User:
    existing_user = getattr(request.state, "current_user", None)
    if existing_user is not None:
        return existing_user

    if x_user_id:
        user = rbac_service.resolve_user(x_user_id)
        request.state.current_user = user
        return user

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token or X-User-Id header.")
    if credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme.")

    user = auth_service.resolve_user_from_token(credentials.credentials)
    request.state.current_user = user
    return user
