# RBAC for RAG Backend

## Roles and permissions

| Role | Core permissions |
|---|---|
| Standard User | `read:document`, `search:document` |
| Power User | Standard + `ingest:document`, `update:document` |
| Document Administrator | Power + `delete:document` |
| Compliance Officer | `read:document`, `search:document`, `read:audit-log`, `export:audit-log` |
| System Administrator | Document Admin + `manage:users`, `manage:roles`, `manage:system` |
| Super Administrator | All permissions |

The source of truth for this matrix is `app/security/policies.py`.

## Validation flow

1. `RBACMiddleware` reads `X-User-Id` and resolves the user from `RBACService`.
2. Route decorators (`@require_roles`, `@require_permissions`) attach required claims to endpoints.
3. Middleware enforces role and permission checks before the endpoint executes.
4. Document-level checks are executed via `RBACService.enforce_document_access`.

## Code example

```python
@router.get('/documents/{document_id}/access')
@require_permissions(Permission.READ_DOCUMENT)
def verify_document_access(
    document_id: str,
    current_user: User = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> DocumentAccessResponse:
    rbac_service.enforce_document_access(current_user, document_id)
    return DocumentAccessResponse(document_id=document_id, message="Access granted")
```

`enforce_document_access` uses a deny-by-default model and grants access only when one of these is true:
- user has a global-access role,
- user is document owner,
- user is explicitly allowed by user ID,
- user is explicitly allowed through a role,
- document is present in the user's allow list.
