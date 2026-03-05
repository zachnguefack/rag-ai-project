from __future__ import annotations

from pydantic import BaseModel

from app.security.policies import Permission


class PermissionCheckResult(BaseModel):
    granted: bool
    permission: Permission
    reason: str
