from __future__ import annotations

from pathlib import Path

from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.database.sqlite import SQLiteStore
from app.models.persistence.document import DocumentMetadata, DocumentRecord, DocumentVersionRecord
from app.security.policies import RoleName
from app.services.rbac_service import RBACService


def test_rbac_assignments_persist_when_repositories_are_reinitialized(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"

    store_first = SQLiteStore(db_path)
    users_first = UserRepository(store_first)
    docs_first = DocumentRepository(store_first)
    dept_access_first = UserDepartmentAccessRepository(store_first)
    doc_access_first = UserDocumentAccessRepository(store_first)

    user = users_first.create_with_id(
        user_id="u-persist",
        username="persisted_user",
        email="persisted@example.com",
        password_hash="hash",
        roles=[RoleName.STANDARD_USER],
        department_id="dept-general",
    )
    docs_first.upsert(
        DocumentRecord(
            document_id="doc-persist",
            title="Persistent Policy",
            department_id="dept-ops",
            owner="u-admin",
            classification="internal",
            document_type="policy",
            status="active",
            versions=[
                DocumentVersionRecord(
                    version=1,
                    content="policy",
                    metadata=DocumentMetadata(
                        department_id="dept-ops",
                        owner="u-admin",
                        classification="internal",
                        document_type="policy",
                        status="active",
                    ),
                )
            ],
        )
    )
    dept_access_first.assign(user_id=user.user_id, department_id="dept-ops", assigned_by="u-admin")
    doc_access_first.upsert_grant(user_id=user.user_id, document_id="doc-persist", granted_by="u-admin")

    rbac_first = RBACService(
        user_repository=users_first,
        document_repository=docs_first,
        user_department_access_repository=dept_access_first,
        user_document_access_repository=doc_access_first,
    )
    roles_after_assign = rbac_first.assign_user_role(user.user_id, RoleName.POWER_USER)
    assert set(roles_after_assign) == {RoleName.STANDARD_USER, RoleName.POWER_USER}

    store_second = SQLiteStore(db_path)
    users_second = UserRepository(store_second)
    docs_second = DocumentRepository(store_second)
    dept_access_second = UserDepartmentAccessRepository(store_second)
    doc_access_second = UserDocumentAccessRepository(store_second)
    rbac_second = RBACService(
        user_repository=users_second,
        document_repository=docs_second,
        user_department_access_repository=dept_access_second,
        user_document_access_repository=doc_access_second,
    )

    persisted_user = users_second.get(user.user_id)
    assert persisted_user is not None
    assert set(persisted_user.roles) == {RoleName.STANDARD_USER, RoleName.POWER_USER}

    persisted_departments = dept_access_second.list_departments_for_user(user.user_id)
    assert [assignment.department_id for assignment in persisted_departments] == ["dept-ops"]

    persisted_grants = doc_access_second.list_for_user(user.user_id)
    assert len(persisted_grants) == 1
    assert persisted_grants[0].document_id == "doc-persist"
    assert persisted_grants[0].is_active is True
