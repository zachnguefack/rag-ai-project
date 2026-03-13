# RBAC and Access Control for the FastAPI Backend

This document describes how authorization is implemented in the running backend (`backend/app`) and how to validate behavior from Swagger or tests.

## Roles and permissions

Role/permission policy is code-defined in `backend/app/security/policies.py` and enforced through `RBACService` + route dependencies/middleware.

| Role | Core permissions |
|---|---|
| Standard User | `read:document`, `search:document` |
| Power User | Standard + `ingest:document`, `update:document` |
| Document Administrator | Power + `delete:document` |
| Compliance Officer | `read:document`, `search:document`, `read:audit-log`, `export:audit-log` |
| System Administrator | Document Admin + `manage:users`, `manage:roles`, `manage:system` |
| Super Administrator | All permissions |

## Authentication and identity sources

The API supports both identity paths:

1. **JWT bearer token** from `POST /api/v1/auth/login`.
2. **`X-User-Id` header** for local/dev/test simulation.

`X-User-Id` is rejected outside local/dev/test-style environments unless unauthenticated mode is enabled (`RAG_ALLOW_UNAUTHENTICATED=true`).

## Enforcement flow

1. `RBACMiddleware` applies route-guard prechecks for high-risk endpoints.
2. `get_current_user` resolves identity (middleware cache -> `X-User-Id` -> bearer token).
3. Route-level permission checks (`@require_permissions`) run.
4. Service-level checks in `RBACService` / `DocumentAccessService` enforce deny-by-default semantics.

## Department and document access model

The backend uses multi-department scope resolution:

- Users may belong to **multiple departments** (`user_department_access`).
- Users may have explicit per-document grants/revocations (`user_document_access`).

Effective scope formula:

`authorized_document_ids = docs_in_assigned_departments UNION active_explicit_grants MINUS revoked_grants`

This computed scope is reused by:

- `GET /api/v1/documents` style metadata operations.
- `POST /api/v1/rag/query` and `POST /api/v1/chat/ask` retrieval filters.

## Admin endpoints relevant to RBAC/access

All endpoints are under `/api/v1/admin`.

### Roles & permissions
- `GET /roles`
- `GET /roles/{role}`
- `GET /permissions`
- `GET /users/{user_id}/roles`
- `PUT /users/{user_id}/roles`
- `POST /users/{user_id}/roles/{role}`
- `DELETE /users/{user_id}/roles/{role}`
- `GET /rbac/matrix`
- `POST /rbac/validate`
- `PUT /roles/{role}/permissions` (immutable policy endpoint -> `400`)

### Department/document access administration
- `POST /users/{user_id}/departments/{department_id}`
- `DELETE /users/{user_id}/departments/{department_id}`
- `GET /users/{user_id}/departments`
- `GET /departments/{department_id}/users`
- `POST /users/{user_id}/document-access`
- `GET /users/{user_id}/document-access`
- `DELETE /users/{user_id}/document-access/{document_id}`
- `GET /users/{user_id}/document-scope`

## Troubleshooting retrieval authorization

If metadata endpoints show documents but RAG returns no evidence:

1. Confirm the same vector collection is used for ingestion and query runtime.
2. Confirm vector chunks exist for those sources.
3. Confirm chunk metadata includes `department_id` + `document_id`.
4. Confirm metadata key parity (`source`, `source_path`) with filter construction.
5. Confirm similarity threshold/top-k settings are not too strict.

`indexed=true` indicates indexing completion in metadata records; it should be correlated with chunk presence in the configured collection.
