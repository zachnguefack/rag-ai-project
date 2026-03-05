from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.security.policies import Permission, RoleName


def require_roles(*roles: RoleName) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    role_set = frozenset(roles)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "required_roles", role_set)
        return func

    return decorator


def require_permissions(*permissions: Permission) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    permission_set = frozenset(permissions)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "required_permissions", permission_set)
        return func

    return decorator
