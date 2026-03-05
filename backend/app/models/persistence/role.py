from __future__ import annotations

from pydantic import BaseModel

from app.security.policies import Permission, RoleName


class RoleRecord(BaseModel):
    name: RoleName
    permissions: list[Permission]
