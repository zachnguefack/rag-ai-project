from __future__ import annotations

from dataclasses import dataclass

from app.security.policies import Permission, RoleName


@dataclass(slots=True, frozen=True)
class Role:
    name: RoleName
    permissions: frozenset[Permission]

    def grants(self, permission: Permission) -> bool:
        return permission in self.permissions
