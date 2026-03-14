from __future__ import annotations

from pathlib import Path
import os
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import FastAPI, HTTPException
from starlette.datastructures import UploadFile

pytest.importorskip("multipart")

from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.document_repo import DocumentRepository
from app.database.sqlite import SQLiteStore
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName
from app.services.department_ingestion_service import DepartmentIngestionService
from app.services.department_service import DepartmentService


def _admin_user() -> User:
    role = Role(name=RoleName.SYSTEM_ADMINISTRATOR, permissions=frozenset({Permission.MANAGE_USERS, Permission.INGEST_DOCUMENT}))
    return User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-general", roles=(role,))


def test_upload_openapi_schema_uses_multipart_binary_files() -> None:
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    schema = app.openapi()
    endpoint = schema["paths"]["/api/v1/admin/departments/{department_id}/upload"]["post"]
    multipart = endpoint["requestBody"]["content"]["multipart/form-data"]["schema"]
    files_schema = schema["components"]["schemas"][multipart["$ref"].split("/")[-1]]["properties"]["files"]

    assert files_schema["type"] == "array"
    assert files_schema["items"]["type"] == "string"
    assert files_schema["items"].get("format") == "binary" or files_schema["items"].get("contentMediaType") == "application/octet-stream"


def test_ingest_file_path_rejects_outside_allowed_roots_with_clear_message(tmp_path: Path) -> None:
    settings = BackendSettings(
        data_dir=tmp_path,
        data_departments_root=tmp_path / "depart",
        metadata_db_path=tmp_path / "metadata.db",
        ingest_allowed_roots=str(tmp_path),
    )
    store = SQLiteStore(settings.metadata_db_path)
    dept_service = DepartmentService(department_repository=DepartmentRepository(store), settings=settings)
    dept_service.create_department(None, "A", "")
    service = DepartmentIngestionService(department_service=dept_service, document_repository=DocumentRepository(store), settings=settings)

    with pytest.raises(HTTPException) as exc:
        service.ingest_file_path(user=_admin_user(), department_id="a", file_path="/etc/passwd")

    assert exc.value.status_code == 400
    assert "outside allowed ingest roots" in str(exc.value.detail)


@pytest.mark.anyio
async def test_upload_with_unsupported_file_has_no_partial_side_effects(tmp_path: Path) -> None:
    settings = BackendSettings(
        data_dir=tmp_path,
        data_departments_root=tmp_path / "depart",
        metadata_db_path=tmp_path / "metadata.db",
        ingest_allowed_roots=str(tmp_path),
    )
    store = SQLiteStore(settings.metadata_db_path)
    dept_service = DepartmentService(department_repository=DepartmentRepository(store), settings=settings)
    dept_service.create_department(None, "A", "")
    repo = DocumentRepository(store)
    service = DepartmentIngestionService(department_service=dept_service, document_repository=repo, settings=settings)

    txt_payload = SpooledTemporaryFile()
    txt_payload.write(b"ok")
    txt_payload.seek(0)
    bad_payload = SpooledTemporaryFile()
    bad_payload.write(b"bad")
    bad_payload.seek(0)

    files = [
        UploadFile(file=txt_payload, filename="safe.txt"),
        UploadFile(file=bad_payload, filename="evil.exe"),
    ]

    with pytest.raises(HTTPException) as exc:
        await service.ingest_upload(user=_admin_user(), department_id="a", files=files)

    assert exc.value.status_code == 400
    assert repo.list() == []


def test_ingest_file_path_accepts_unc_style_paths_with_allowed_root(tmp_path: Path) -> None:
    smb_root = tmp_path / "network" / "server" / "share"
    smb_root.mkdir(parents=True)
    source = smb_root / "source.txt"
    source.write_text("network", encoding="utf-8")

    settings = BackendSettings(
        data_dir=tmp_path,
        data_departments_root=tmp_path / "depart",
        metadata_db_path=tmp_path / "metadata.db",
        ingest_allowed_roots=f"{tmp_path}{os.pathsep}{smb_root}",
    )
    store = SQLiteStore(settings.metadata_db_path)
    dept_service = DepartmentService(department_repository=DepartmentRepository(store), settings=settings)
    dept_service.create_department(None, "A", "")
    service = DepartmentIngestionService(department_service=dept_service, document_repository=DocumentRepository(store), settings=settings)

    unc_path = "\\\\server\\share\\source.txt"
    mapped_unc = str(source).replace(str(smb_root), "//server/share")
    assert service._coerce_filesystem_path(unc_path).as_posix() == Path(mapped_unc).as_posix()


def test_ingest_file_path_returns_403_for_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.txt"
    source.write_text("x", encoding="utf-8")

    settings = BackendSettings(
        data_dir=tmp_path,
        data_departments_root=tmp_path / "depart",
        metadata_db_path=tmp_path / "metadata.db",
        ingest_allowed_roots=str(tmp_path),
    )
    store = SQLiteStore(settings.metadata_db_path)
    dept_service = DepartmentService(department_repository=DepartmentRepository(store), settings=settings)
    dept_service.create_department(None, "A", "")
    service = DepartmentIngestionService(department_service=dept_service, document_repository=DocumentRepository(store), settings=settings)

    def _raise_permission(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("app.services.department_ingestion_service.shutil.copy2", _raise_permission)

    with pytest.raises(HTTPException) as exc:
        service.ingest_file_path(user=_admin_user(), department_id="a", file_path=str(source))

    assert exc.value.status_code == 403
