from __future__ import annotations

from app.database.repositories.audit_repo import AuditLogRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName
from app.services.audit_service import AuditService
from app.services.document_access_service import DocumentAccessService
from app.services.document_service import DocumentService
from app.services.rbac_service import RBACService
from app.services.scope_builder_service import ScopeBuilderService


STANDARD_ROLE = Role(name=RoleName.STANDARD_USER, permissions=frozenset({Permission.READ_DOCUMENT, Permission.SEARCH_DOCUMENT}))
ADMIN_ROLE = Role(name=RoleName.SYSTEM_ADMINISTRATOR, permissions=frozenset({Permission.READ_DOCUMENT, Permission.MANAGE_USERS, Permission.READ_AUDIT_LOG}))


def _build_services() -> tuple[DocumentService, DocumentAccessService]:
    documents = DocumentRepository()
    access_repo = UserDocumentAccessRepository()
    rbac = RBACService(document_repository=documents, user_document_access_repository=access_repo)
    scope_builder = ScopeBuilderService(documents, access_repo)
    access_service = DocumentAccessService(
        document_repository=documents,
        user_document_access_repository=access_repo,
        scope_builder=scope_builder,
        rbac_service=rbac,
    )
    audit = AuditService(repository=AuditLogRepository())
    service = DocumentService(
        document_repository=documents,
        rbac_service=rbac,
        document_access_service=access_service,
        user_document_access_repository=access_repo,
        audit_service=audit,
    )
    return service, access_service


def test_visible_document_listing_is_scope_aware() -> None:
    service, _ = _build_services()
    user = User(user_id="u-standard", username="std", email="std@example.com", department_id="dept-operations", roles=(STANDARD_ROLE,))

    response = service.list_visible_documents(user, limit=10, offset=0, department_id=None, document_type=None, classification=None, status_value=None, owner=None)

    assert response.total == 1
    assert response.items[0].document_id == "doc-ops"


def test_search_returns_only_authorized_matches() -> None:
    service, access_service = _build_services()
    user = User(user_id="u-standard", username="std", email="std@example.com", department_id="dept-operations", roles=(STANDARD_ROLE,))
    access_service.grant_document_access(user_id="u-standard", document_id="doc-eng", granted_by="u-admin")

    response = service.search_visible_documents(
        user,
        query="engineering",
        limit=10,
        offset=0,
        department_id=None,
        document_type=None,
        classification=None,
        status_value=None,
        owner=None,
    )

    assert response.total == 1
    assert response.items[0].document_id == "doc-eng"


def test_admin_reassign_department_updates_metadata() -> None:
    service, _ = _build_services()
    admin = User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-operations", roles=(ADMIN_ROLE,))

    updated = service.reassign_document_department(admin, "doc-ops", "dept-engineering")

    assert updated.department_id == "dept-engineering"
