from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName


class _PermissiveRBAC:
    def enforce_permission(self, user: User, permission: Permission) -> None:
        if permission not in user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No assigned role grants this permission.")


def _admin_user() -> User:
    role = Role(name=RoleName.SYSTEM_ADMINISTRATOR, permissions=frozenset({Permission.MANAGE_USERS, Permission.MANAGE_ROLES, Permission.INGEST_DOCUMENT, Permission.READ_DOCUMENT}))
    return User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-general", roles=(role,))


def _build_client(tmp_path: Path) -> TestClient:
    # Reset runtime singletons to ensure each test uses its own settings/root.
    deps._runtime_settings = None
    deps._runtime_department_service = None
    deps._runtime_department_repo = None
    deps._runtime_document_repo = None
    deps._runtime_user_document_access_repo = None
    deps._runtime_user_department_access_repo = None
    deps._runtime_user_repo = None
    deps._runtime_service = None
    deps._runtime_sqlite_store = None

    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db")
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_current_user] = _admin_user
    app.dependency_overrides[deps.get_rbac_service] = _PermissiveRBAC
    app.dependency_overrides[deps.get_rag_service] = lambda: None

    user_repo = deps.get_user_repository()
    user_repo.create_with_id(
        user_id="u-target",
        username="john",
        email="john@example.com",
        password_hash="hashed",
        roles=[RoleName.STANDARD_USER],
        department_id="dept-general",
    )

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


def test_department_documents_listing_is_lightweight_contract(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_department = client.post("/api/v1/admin/departments", json={"name": "Operations", "description": "Ops"})
    assert create_department.status_code == 200

    create_document = client.post(
        "/api/v1/documents",
        json={
            "document_id": "doc-ops-list-1",
            "title": "Ops Checklist",
            "content": "Checklist content",
            "metadata": {
                "department_id": "operations",
                "owner": "u-admin",
                "classification": "internal",
                "document_type": "policy",
                "status": "active",
            },
        },
    )
    assert create_document.status_code == 200

    response = client.get("/api/v1/admin/departments/operations/documents")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body

    item = body[0]
    assert "content" not in item
    assert "metadata" not in item
    assert "storage_path" in item
    assert "department_id" in item
    assert "document_id" in item


def test_department_documents_openapi_uses_listing_item_schema() -> None:
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    schema = app.openapi()
    operation = schema["paths"]["/api/v1/admin/departments/{department_id}/documents"]["get"]
    items_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]["items"]

    assert items_schema["$ref"].endswith("/DepartmentDocumentListItemResponse")


def test_user_department_assignment_endpoints_and_openapi(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    assert client.post("/api/v1/admin/departments", json={"name": "IT", "description": "IT docs"}).status_code == 200

    assign = client.post("/api/v1/admin/users/u-target/departments/it")
    assert assign.status_code == 200
    assert assign.json()["department_id"] == "it"

    list_user = client.get("/api/v1/admin/users/u-target/departments")
    assert list_user.status_code == 200
    assert any(item["department_id"] == "it" for item in list_user.json())

    list_department = client.get("/api/v1/admin/departments/it/users")
    assert list_department.status_code == 200
    assert any(item["user_id"] == "u-target" for item in list_department.json())

    remove = client.delete("/api/v1/admin/users/u-target/departments/it")
    assert remove.status_code == 200


def test_user_department_assignment_requires_manage_users_permission(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    role = Role(name=RoleName.STANDARD_USER, permissions=frozenset({Permission.READ_DOCUMENT}))
    client.app.dependency_overrides[deps.get_current_user] = lambda: User(
        user_id="u-basic", username="basic", email="basic@example.com", department_id="dept-general", roles=(role,)
    )

    assert client.post("/api/v1/admin/departments", json={"name": "HR", "description": "HR docs"}).status_code == 403


def _build_client_with_real_rbac(tmp_path: Path) -> TestClient:
    deps._runtime_settings = None
    deps._runtime_department_service = None
    deps._runtime_department_repo = None
    deps._runtime_document_repo = None
    deps._runtime_user_document_access_repo = None
    deps._runtime_user_department_access_repo = None
    deps._runtime_user_repo = None
    deps._runtime_service = None
    deps._runtime_sqlite_store = None
    deps._runtime_rbac = None

    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db")
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_current_user] = _admin_user
    app.dependency_overrides[deps.get_rag_service] = lambda: None

    user_repo = deps.get_user_repository()
    user_repo.create_with_id(
        user_id="u-target",
        username="john",
        email="john@example.com",
        password_hash="hashed",
        roles=[RoleName.STANDARD_USER],
        department_id="dept-general",
    )

    return TestClient(app)


def test_user_role_assignment_endpoints_and_openapi(tmp_path: Path) -> None:
    client = _build_client_with_real_rbac(tmp_path)

    assign = client.post("/api/v1/admin/users/u-target/roles/power_user")
    assert assign.status_code == 200
    assert {role for role in assign.json()["roles"]} == {"standard_user", "power_user"}

    remove = client.delete("/api/v1/admin/users/u-target/roles/standard_user")
    assert remove.status_code == 200
    assert remove.json()["roles"] == ["power_user"]

    replace = client.put("/api/v1/admin/users/u-target/roles", json={"roles": ["compliance_officer"]})
    assert replace.status_code == 200
    assert replace.json()["roles"] == ["compliance_officer"]

    schema = client.app.openapi()
    assert "/api/v1/admin/users/{user_id}/roles/{role}" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/admin/users/{user_id}/roles/{role}"]
    assert "delete" in schema["paths"]["/api/v1/admin/users/{user_id}/roles/{role}"]
