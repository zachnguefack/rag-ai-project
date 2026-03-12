from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config.settings import BackendSettings
from app.database.repositories.department_repo import DepartmentRepository
from app.database.repositories.user_department_access_repo import UserDepartmentAccessRepository
from app.database.repositories.user_repo import UserRepository
from app.database.sqlite import SQLiteStore
from app.models.persistence.department import DepartmentRecord
from app.security.policies import RoleName
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService


class AuthDepartmentResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore(Path(tempfile.gettempdir()) / "rag-auth-dept-resolution-test.db")
        with self.store.connection() as conn:
            conn.execute("DELETE FROM user_department_access")
            conn.execute("DELETE FROM user_document_access")
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM departments")

        self.departments = DepartmentRepository(self.store)
        self.department_access = UserDepartmentAccessRepository(self.store)
        self.users = UserRepository(self.store)

        self.departments.upsert(
            DepartmentRecord(
                department_id="finance",
                name="Finance",
                slug="finance",
                description="",
            )
        )
        self.departments.upsert(
            DepartmentRecord(
                department_id="it",
                name="IT",
                slug="it",
                description="",
            )
        )

        settings = BackendSettings(jwt_secret_key="test-secret", jwt_access_token_expire_minutes=30)
        self.auth = AuthService(
            settings=settings,
            user_repository=self.users,
            user_department_access_repository=self.department_access,
        )
        self.rbac = RBACService(
            user_repository=self.users,
            user_department_access_repository=self.department_access,
        )

    def test_auth_hydration_prefers_rbac_assignments_over_legacy_default(self) -> None:
        record = self.users.create(
            username="admin",
            email="admin@example.com",
            password_hash="hash",
            roles=[RoleName.SUPER_ADMINISTRATOR],
            department_id="dept-general",
        )
        self.department_access.assign(user_id=record.user_id, department_id="it", assigned_by="u-root")

        user = self.auth.hydrate_user(record)

        self.assertEqual(user.department_id, "it")
        self.assertEqual(user.department_ids, ("it",))

    def test_auth_resolve_from_token_uses_current_rbac_assignments(self) -> None:
        record = self.users.create(
            username="ops",
            email="ops@example.com",
            password_hash="hash",
            roles=[RoleName.STANDARD_USER],
            department_id="dept-general",
        )
        self.department_access.assign(user_id=record.user_id, department_id="finance", assigned_by="u-root")
        token, _ = self.auth.issue_access_token(record)

        user = self.auth.resolve_user_from_token(token)

        self.assertEqual(user.department_id, "finance")
        self.assertEqual(user.department_ids, ("finance",))

    def test_rbac_and_auth_share_the_same_department_scope(self) -> None:
        record = self.users.create(
            username="multi",
            email="multi@example.com",
            password_hash="hash",
            roles=[RoleName.STANDARD_USER],
            department_id="dept-general",
        )
        self.department_access.assign(user_id=record.user_id, department_id="it", assigned_by="u-root")
        self.department_access.assign(user_id=record.user_id, department_id="finance", assigned_by="u-root")

        auth_user = self.auth.hydrate_user(record)
        rbac_user = self.rbac.resolve_user(record.user_id)

        self.assertEqual(auth_user.department_ids, rbac_user.department_ids)
        self.assertEqual(auth_user.department_id, rbac_user.department_id)


if __name__ == "__main__":
    unittest.main()
