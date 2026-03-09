from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException

pytest.importorskip("multipart")

from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings
from app.database.repositories.document_repo import DocumentRepository
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
    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", ingest_allowed_roots=str(tmp_path))
    dept_service = DepartmentService(settings=settings)
    dept_service.create_department(None, "A", "")
    service = DepartmentIngestionService(
        department_service=dept_service,
        document_repository=DocumentRepository(),
        settings=settings,
    )

    with pytest.raises(HTTPException) as exc:
        service.ingest_file_path(user=_admin_user(), department_id="a", file_path="/etc/passwd")

    assert exc.value.status_code == 400
    assert "outside allowed ingest roots" in str(exc.value.detail)
