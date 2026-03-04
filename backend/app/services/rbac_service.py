class RBACService:
    ROLE_PERMISSIONS = {
        "admin": {"admin:read", "document:read", "document:write", "rag:query", "user:read"},
        "reader": {"document:read", "rag:query", "user:read"},
    }

    def has_permission(self, roles: list[str], permission: str) -> bool:
        return any(permission in self.ROLE_PERMISSIONS.get(role, set()) for role in roles)
