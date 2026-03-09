from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.config.settings import BackendSettings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.repositories.user_document_access_repo import UserDocumentAccessRepository
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName
from app.services.department_ingestion_service import DepartmentIngestionService
from app.services.department_service import DepartmentService
from app.services.rbac_service import RBACService


class FakeRAGService:
    def __init__(self) -> None:
        self.removed: list[str] = []

    def run_indexing(self, force_reindex: bool) -> dict:
        _ = force_reindex
        return {"indexed_files": 1, "indexed_chunks": 1, "removed_files": 0, "reused_existing_index": False}

    def remove_document_sources(self, sources: list[str]) -> None:
        self.removed.extend(sources)


def _admin_user() -> User:
    role = Role(name=RoleName.SYSTEM_ADMINISTRATOR, permissions=frozenset({Permission.MANAGE_USERS, Permission.INGEST_DOCUMENT}))
    return User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-general", roles=(role,))


def test_department_creation_creates_repository_folder(tmp_path: Path) -> None:
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart")
    service = DepartmentService(settings=settings)

    service.create_department(None, "QA", "Quality", actor_user_id="u-admin")

    assert (tmp_path / "depart" / "qa").is_dir()


def test_department_deletion_removes_docs_files_and_vectors(tmp_path: Path) -> None:
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart")
    rag = FakeRAGService()
    depts = DepartmentRepository()
    docs = DocumentRepository()
    access = UserDocumentAccessRepository()
    service = DepartmentService(department_repository=depts, document_repository=docs, user_document_access_repository=access, settings=settings, rag_service=rag)

    created = service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    dept_id = created.department_id
    assert created.department_id == "qa"
    storage = tmp_path / "depart" / "qa" / "qa.txt"
    storage.write_text("qa content", encoding="utf-8")
    admin = _admin_user()

    ingest = DepartmentIngestionService(
        department_service=service,
        document_repository=docs,
        rag_service=rag,
        rbac_service=RBACService(document_repository=docs),
        settings=settings,
    )
    ingest.ingest_file_path(user=admin, department_id=dept_id, file_path=str(storage))

    result = service.delete_department(dept_id, actor_user_id="u-admin")

    assert result["deleted_documents"] >= 1
    assert not (tmp_path / "depart" / "qa").exists()
    assert rag.removed


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart")
    depts = DepartmentRepository()
    docs = DocumentRepository()
    service = DepartmentService(department_repository=depts, document_repository=docs, settings=settings)
    created = service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    dept_id = created.department_id

    ingest = DepartmentIngestionService(
        department_service=service,
        document_repository=docs,
        settings=settings,
        rbac_service=RBACService(document_repository=docs),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ingest.ingest_upload(
                user=_admin_user(),
                department_id=dept_id,
                files=[UploadFile(filename="malware.exe", file=BytesIO(b"x"))],
            )
        )

    assert exc.value.status_code == 400
    assert "Unsupported file type" in exc.value.detail


def test_upload_rejects_file_larger_than_configured_limit(tmp_path: Path) -> None:
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", max_upload_file_size_bytes=4)
    depts = DepartmentRepository()
    docs = DocumentRepository()
    service = DepartmentService(department_repository=depts, document_repository=docs, settings=settings)
    created = service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    dept_id = created.department_id

    ingest = DepartmentIngestionService(
        department_service=service,
        document_repository=docs,
        settings=settings,
        rbac_service=RBACService(document_repository=docs),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ingest.ingest_upload(
                user=_admin_user(),
                department_id=dept_id,
                files=[UploadFile(filename="big.txt", file=BytesIO(b"12345"))],
            )
        )

    assert exc.value.status_code == 413
    assert "exceeds max upload size" in exc.value.detail
