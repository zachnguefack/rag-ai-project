from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.config.settings import BackendSettings
from app.models.domain.role import Role
from app.models.domain.user import User
from app.security.policies import Permission, RoleName


class _FakeAuthService:
    def resolve_user_from_token(self, token: str) -> User:  # pragma: no cover - not used in this test
        raise AssertionError("bearer auth should not be used in this scenario")


class _FakeRBACService:
    def resolve_user(self, user_id: str) -> User:
        role = Role(name=RoleName.STANDARD_USER, permissions=frozenset({Permission.READ_DOCUMENT}))
        return User(
            user_id=user_id,
            username="test-user",
            email="test@example.com",
            department_id="finance",
            roles=(role,),
        )


def test_x_user_id_header_is_disabled_in_production() -> None:
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user: User = Depends(deps.get_current_user)) -> dict[str, str]:
        return {"user_id": user.user_id}

    app.dependency_overrides[deps.get_settings] = lambda: BackendSettings(app_env="production", allow_unauthenticated=False)
    app.dependency_overrides[deps.get_auth_service] = lambda: _FakeAuthService()
    app.dependency_overrides[deps.get_rbac_service] = lambda: _FakeRBACService()

    client = TestClient(app)
    response = client.get("/whoami", headers={"X-User-Id": "u-123"})

    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-Id header is disabled in this environment."
