from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.config.settings import BackendSettings
from app.database.sqlite import SQLiteStore
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


def _build(tmp_path: Path):
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db")
    store = SQLiteStore(settings.metadata_db_path)
    docs = DocumentRepository(store)
    depts = DepartmentRepository(store)
    service = DepartmentService(department_repository=depts, document_repository=docs, user_document_access_repository=UserDocumentAccessRepository(), settings=settings)
    return settings, service, docs


def test_department_creation_persists_metadata_and_creates_folder(tmp_path: Path) -> None:
    _, service, _ = _build(tmp_path)
    service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    assert (tmp_path / "depart" / "qa").is_dir()


def test_upload_persists_metadata_and_file_survives_restart(tmp_path: Path) -> None:
    settings, service, docs = _build(tmp_path)
    service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    ingest = DepartmentIngestionService(department_service=service, document_repository=docs, settings=settings, rbac_service=RBACService(document_repository=docs))

    asyncio.run(ingest.ingest_upload(user=_admin_user(), department_id="qa", files=[UploadFile(filename="a.txt", file=BytesIO(b"hello"))]))
    assert len(docs.list_by_department("qa")) == 1

    # restart services using same metadata DB and filesystem root
    _, service2, docs2 = _build(tmp_path)
    files = service2.list_department_files("qa")
    assert len(files) == 1
    assert docs2.list_by_department("qa")[0].stored_filename == "a.txt"


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    settings, service, docs = _build(tmp_path)
    service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    ingest = DepartmentIngestionService(department_service=service, document_repository=docs, settings=settings, rbac_service=RBACService(document_repository=docs))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ingest.ingest_upload(user=_admin_user(), department_id="qa", files=[UploadFile(filename="bad.exe", file=BytesIO(b"x"))]))

    assert exc.value.status_code == 400


def test_upload_rejects_file_larger_than_configured_limit(tmp_path: Path) -> None:
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db", max_upload_file_size_bytes=4)
    store = SQLiteStore(settings.metadata_db_path)
    docs = DocumentRepository(store)
    depts = DepartmentRepository(store)
    service = DepartmentService(department_repository=depts, document_repository=docs, settings=settings)
    service.create_department(None, "QA", "Quality", actor_user_id="u-admin")
    ingest = DepartmentIngestionService(department_service=service, document_repository=docs, settings=settings, rbac_service=RBACService(document_repository=docs))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(ingest.ingest_upload(user=_admin_user(), department_id="qa", files=[UploadFile(filename="a.txt", file=BytesIO(b"12345"))]))

    assert exc.value.status_code == 413
