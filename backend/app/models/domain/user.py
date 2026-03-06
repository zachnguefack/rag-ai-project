from __future__ import annotations

from dataclasses import dataclass, field

from app.models.domain.role import Role
from app.security.policies import Permission, RoleName


@dataclass(slots=True)
class User:
    user_id: str
    username: str
    email: str
    is_active: bool = True
    roles: tuple[Role, ...] = field(default_factory=tuple)
    document_allow_list: frozenset[str] = field(default_factory=frozenset)
    department: str = "general"
    classification_level: str = "internal"
    allowed_document_scopes: frozenset[str] = field(default_factory=frozenset)

    @property
    def role_names(self) -> frozenset[RoleName]:
        return frozenset(role.name for role in self.roles)

    @property
    def permissions(self) -> frozenset[Permission]:
        aggregated: set[Permission] = set()
        for role in self.roles:
            aggregated.update(role.permissions)
        return frozenset(aggregated)
