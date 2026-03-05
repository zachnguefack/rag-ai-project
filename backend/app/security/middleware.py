from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.security.policies import Permission, RoleName
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService


@dataclass(frozen=True)
class RouteGuard:
    method: str
    path_pattern: re.Pattern[str]
    required_roles: frozenset[RoleName] = frozenset()
    required_permissions: frozenset[Permission] = frozenset()


class RBACMiddleware(BaseHTTPMiddleware):
    """Enterprise-style deny-by-default RBAC gate for protected API routes."""

    def __init__(self, app, rbac_service: RBACService, auth_service: AuthService):
        super().__init__(app)
        self._rbac = rbac_service
        self._auth = auth_service
        self._guards = (
            RouteGuard(
                method="POST",
                path_pattern=re.compile(r"^/api/v1/documents/index$"),
                required_roles=frozenset(
                    {
                        RoleName.POWER_USER,
                        RoleName.DOCUMENT_ADMINISTRATOR,
                        RoleName.SYSTEM_ADMINISTRATOR,
                        RoleName.SUPER_ADMINISTRATOR,
                    }
                ),
                required_permissions=frozenset({Permission.INGEST_DOCUMENT}),
            ),
            RouteGuard(
                method="GET",
                path_pattern=re.compile(r"^/api/v1/documents/[^/]+/access$"),
                required_permissions=frozenset({Permission.READ_DOCUMENT}),
            ),
        )

    async def dispatch(self, request: Request, call_next):
        guard = self._match_guard(request.method, request.url.path)
        if guard is None:
            return await call_next(request)

        try:
            authorization = request.headers.get("authorization")
            if not authorization:
                raise HTTPException(status_code=401, detail="Missing Authorization header.")
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise HTTPException(status_code=401, detail="Invalid authorization scheme.")

            user = self._auth.resolve_user_from_token(token)
            request.state.current_user = user

            if guard.required_roles:
                self._rbac.verify_roles(user, set(guard.required_roles))
            for permission in guard.required_permissions:
                self._rbac.enforce_permission(user, permission)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

        return await call_next(request)

    def _match_guard(self, method: str, path: str) -> RouteGuard | None:
        for guard in self._guards:
            if guard.method == method and guard.path_pattern.match(path):
                return guard
        return None
