from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName


class _PermissiveRBAC:
    def enforce_permission(self, user: User, permission: Permission) -> None:  # pragma: no cover - trivial stub
        _ = (user, permission)


def _admin_user() -> User:
    role = Role(name=RoleName.SYSTEM_ADMINISTRATOR, permissions=frozenset({Permission.MANAGE_USERS}))
    return User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-general", roles=(role,))


def _build_client(tmp_path: Path) -> TestClient:
    # Reset runtime singletons to ensure each test uses its own settings/root.
    deps._runtime_settings = None
    deps._runtime_department_service = None
    deps._runtime_department_repo = None
    deps._runtime_document_repo = None
    deps._runtime_user_document_access_repo = None
    deps._runtime_service = None
    deps._runtime_sqlite_store = None

    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db")
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_current_user] = _admin_user
    app.dependency_overrides[deps.get_rbac_service] = _PermissiveRBAC
    app.dependency_overrides[deps.get_rag_service] = lambda: None

    return TestClient(app)


def test_departments_endpoints_resolve_dependencies_and_persist_metadata(tmp_path: Path) -> None:
    root = tmp_path / "depart"
    client = _build_client(tmp_path)

    create_response = client.post(
        "/api/v1/admin/departments",
        json={"name": "Research", "description": "R&D docs"},
    )
    assert create_response.status_code == 200
    body = create_response.json()
    assert body["department_id"] == "research"
    assert (root / "research").is_dir()

    list_response = client.get("/api/v1/admin/departments")
    assert list_response.status_code == 200
    listed_ids = {item["department_id"] for item in list_response.json()}
    assert "research" in listed_ids


def test_openapi_still_loads_with_department_routes() -> None:
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    schema = app.openapi()

    assert "/api/v1/admin/departments" in schema["paths"]
