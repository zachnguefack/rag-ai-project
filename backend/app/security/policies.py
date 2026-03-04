def can_access_tenant(user: dict, tenant_id: str) -> bool:
    return user.get("tenant_id") in {None, tenant_id}
