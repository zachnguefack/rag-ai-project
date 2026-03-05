from __future__ import annotations

from app.models.domain.role import Role
from app.security.policies import ROLE_PERMISSION_MAP, RoleName


class RoleRepository:
    def __init__(self) -> None:
        self._roles = {name: Role(name=name, permissions=permissions) for name, permissions in ROLE_PERMISSION_MAP.items()}

    def get(self, role_name: RoleName) -> Role:
        return self._roles[role_name]

    def list(self) -> tuple[Role, ...]:
        return tuple(self._roles.values())
