from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.router import build_v1_router
from app.config.settings import BackendSettings
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.password import verify_password
from app.security.policies import Permission, RoleName


def _admin_user() -> User:
    role = Role(
        name=RoleName.SYSTEM_ADMINISTRATOR,
        permissions=frozenset({
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.READ_DOCUMENT,
            Permission.SEARCH_DOCUMENT,
        }),
    )
    return User(user_id="u-admin", username="admin", email="admin@example.com", department_id="dept-general", roles=(role,))


def _build_client(tmp_path: Path) -> TestClient:
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
    deps._runtime_user_service = None
    deps._runtime_auth = None

    settings = BackendSettings(data_dir=tmp_path, data_departments_root=tmp_path / "depart", metadata_db_path=tmp_path / "metadata.db")
    app = FastAPI()
    app.include_router(build_v1_router(), prefix="/api/v1")

    app.dependency_overrides[deps.get_settings] = lambda: settings
    app.dependency_overrides[deps.get_current_user] = _admin_user
    app.dependency_overrides[deps.get_rag_service] = lambda: None

    return TestClient(app)


def test_admin_user_crud_and_activation_flow(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create = client.post(
        "/api/v1/admin/users",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "Str0ngPassw0rd!",
            "is_active": True,
            "department_ids": [],
            "roles": ["standard_user"],
        },
    )
    assert create.status_code == 201
    user_id = create.json()["user_id"]

    listed = client.get("/api/v1/admin/users", params={"username": "ali"})
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    detail = client.get(f"/api/v1/admin/users/{user_id}")
    assert detail.status_code == 200
    assert detail.json()["email"] == "alice@example.com"

    updated = client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"username": "alice.renamed", "email": "alice.renamed@example.com", "is_active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "alice.renamed"

    patched = client.patch(f"/api/v1/admin/users/{user_id}", json={"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    activated = client.post(f"/api/v1/admin/users/{user_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    deactivated = client.post(f"/api/v1/admin/users/{user_id}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False


def test_admin_reset_and_self_change_password(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create = client.post(
        "/api/v1/admin/users",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "OldPassw0rd!",
            "roles": ["standard_user"],
        },
    )
    assert create.status_code == 201
    user_id = create.json()["user_id"]

    reset = client.post(f"/api/v1/admin/users/{user_id}/reset-password", json={"new_password": "AdminReset1!"})
    assert reset.status_code == 200

    user_repo = deps.get_user_repository()
    record = user_repo.get(user_id)
    assert record is not None
    assert verify_password("AdminReset1!", record.password_hash)

    user_role = Role(name=RoleName.STANDARD_USER, permissions=frozenset({Permission.READ_DOCUMENT, Permission.SEARCH_DOCUMENT}))
    client.app.dependency_overrides[deps.get_current_user] = lambda: User(
        user_id=user_id,
        username="bob",
        email="bob@example.com",
        department_id="",
        roles=(user_role,),
    )

    wrong_current = client.post(
        "/api/v1/users/change-password",
        json={"current_password": "WrongPass1!", "new_password": "NewOwnPass1!"},
    )
    assert wrong_current.status_code == 400

    ok_change = client.post(
        "/api/v1/users/change-password",
        json={"current_password": "AdminReset1!", "new_password": "NewOwnPass1!"},
    )
    assert ok_change.status_code == 200

    changed = user_repo.get(user_id)
    assert changed is not None
    assert verify_password("NewOwnPass1!", changed.password_hash)
