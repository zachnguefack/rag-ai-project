def map_oidc_claims(claims: dict) -> dict:
    return {"sub": claims.get("sub"), "roles": claims.get("roles", [])}
