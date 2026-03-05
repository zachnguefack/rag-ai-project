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

1. `RBACMiddleware` resolves identity from `X-User-Id` (local/dev) or `Authorization: Bearer <token>`.
2. Route decorators (`@require_roles`, `@require_permissions`) define RBAC claims on endpoints.
3. Middleware and endpoint-level RBAC enforcement verify required permissions.
4. Document-level checks are executed via `RBACService.enforce_document_access` (deny-by-default).

## Swagger usage (`/docs`)

Swagger supports all configured security schemes:

- `x-api-key` for backend API key enforcement.
- `Authorization: Bearer <token>` for JWT-authenticated users.
- `X-User-Id` for local/dev identity simulation when testing RBAC flows.

### Local/dev quick start in Swagger

1. Open `/docs`.
2. Expand **Authorize** and provide `x-api-key` if required by environment.
3. For RBAC testing, set `X-User-Id` (e.g., `u-sys-admin`) to resolve a known user.
4. Call endpoints in the **Roles & Permissions** section.

## Admin RBAC endpoints

All endpoints below are under `/api/v1/admin`, tagged as **Roles & Permissions**, and require `manage:roles`.

- `GET /roles` — list all roles and permissions.
- `GET /roles/{role}` — get one role with permissions.
- `GET /permissions` — list all permissions.
- `GET /users/{user_id}/roles` — list user role assignments.
- `PUT /users/{user_id}/roles` — replace a user's full role set.
- `PUT /roles/{role}/permissions` — returns `400` because policy is immutable in API.
- `GET /rbac/matrix` — returns role→permission matrix from `policies.py`.
- `POST /rbac/validate` — validate permission + optional document-level access for a user.

### Example: replace user roles

`PUT /api/v1/admin/users/u-standard/roles`

```json
{
  "roles": ["standard_user", "power_user"]
}
```

Response:

```json
{
  "user_id": "u-standard",
  "roles": ["power_user", "standard_user"]
}
```

### Example: validate access with optional document checks

`POST /api/v1/admin/rbac/validate`

```json
{
  "user_id": "u-power",
  "permission": "read:document",
  "document_id": "doc-public"
}
```

Response:

```json
{
  "user_id": "u-power",
  "permission": "read:document",
  "document_id": "doc-public",
  "allowed": true,
  "reason": "role=power_user"
}
```

If `document_id` is provided, validation uses `RBACService.enforce_document_access` and remains deny-by-default.
