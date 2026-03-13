# Backend Developer Guide (FastAPI Enterprise RAG)

## 1. Architecture at a glance

Runtime entrypoint: `backend/app/main.py`.

Core layers:
- **API** (`backend/app/api/v1`): request validation, endpoint contracts.
- **Services** (`backend/app/services`): business logic (auth, RBAC, document access, ingestion, retrieval).
- **Repositories** (`backend/app/database/repositories`): SQLite persistence.
- **RAG engine wrapper** (`backend/app/services/rag_service.py`): indexing + answer orchestration using `rag_v2`.
- **Security** (`backend/app/security`): JWT, RBAC decorators, middleware route guards.

## 2. Authentication model

### Login / token issuance
- `POST /api/v1/auth/login` authenticates username/password.
- `AuthService.issue_access_token` creates signed access token containing `sub`, `jti`, expiry, and type claims.

### Logout / revocation
- `POST /api/v1/auth/logout` adds token id (`jti`) to in-memory revocation set.
- Revocation is process-local and intended for runtime session invalidation.

### Identity hydration
- `get_current_user` resolves user from request state cache, `X-User-Id`, or bearer token.
- Hydration resolves role permissions and effective department assignments before authorization.

### Environment restrictions
- `X-User-Id` is allowed only in local/dev/test-like environments or when unauthenticated mode is enabled.

## 3. RBAC + department/document access

### Permission enforcement
- Middleware route guards perform prechecks on sensitive routes.
- Endpoint decorators and service-layer checks enforce permissions.

### Effective document scope
- Scope is built in `ScopeBuilderService` from:
  - assigned department documents,
  - active explicit grants,
  - revoked explicit grants.

Formula:
`(department_docs UNION explicit_grants) MINUS revoked_grants`

## 4. Document ingestion and indexing

### Upload flow
Admin upload endpoint: `POST /api/v1/admin/departments/{department_id}/ingest/upload`.

Flow implemented in `DepartmentIngestionService`:
1. Enforce permissions (`ingest:document` + `manage:users`).
2. Validate non-empty batch and extension allowlist.
3. Validate upload size against `RAG_MAX_UPLOAD_FILE_SIZE_BYTES`.
4. Persist files under department filesystem path.
5. Register metadata (`documents` + version record, checksum, storage path).
6. Trigger indexing via `RAGApplicationService.run_indexing`.
7. Mark records indexed on success.

### Filesystem ingestion
- `.../ingest/file-path` and `.../ingest/folder-path` enforce root allowlist via `RAG_INGEST_ALLOWED_ROOTS`.
- Paths outside configured roots are rejected.

## 5. Vector indexing details

Indexing is delegated to `rag_v2` (`SmartIndexer`, `EmbeddingManager`, `VectorStore`) through `RAGApplicationService`.

Operational behavior:
- Chunking strategy configured by `chunk_size` / `chunk_overlap` settings.
- Embeddings generated with configured model + retry policy.
- Vector records persisted in configured collection and directory.
- Incremental state tracked in `index_state.json`.

## 6. Secure RAG retrieval/query flow

Query endpoints:
- `POST /api/v1/rag/query`
- `POST /api/v1/chat/ask` (legacy alias)

Flow:
1. Authenticate and resolve identity.
2. Enforce `search:document` + `read:document`.
3. Compute authorized document IDs.
4. Build vector metadata filters (`department_id`, `document_id`, source/source_path).
5. Execute retrieval + generation via `RetrievalService` -> `RAGApplicationService.answer`.
6. Sanitize citations to authorized scope only (defense in depth).
7. Record audit event.

Strict scope behavior:
- If no authorized docs are available, secure retriever returns deterministic no-evidence response and does not query unrestricted corpus.

## 7. Admin capability overview

Admin APIs include:
- user CRUD/lifecycle and password reset,
- role assignment and RBAC matrix validation,
- department CRUD and listing users/documents/files,
- ingestion endpoints (upload/path/folder),
- per-user department and document grant administration,
- admin document listing/reassignment/audit views,
- audit log browsing endpoints.

## 8. Error handling and logging patterns

- Services raise `HTTPException` with sanitized client-facing details.
- Ingestion and secure retrieval include structured logs for diagnostics.
- Unexpected ingestion failures are logged with stack traces and returned as generic 500 errors.

## 9. Troubleshooting checklist

- Validate API key mode (`RAG_ALLOW_UNAUTHENTICATED`, `RAG_API_KEY`).
- Validate JWT secret and token expiry settings.
- Verify department assignment + explicit grants when access seems denied.
- Verify indexed metadata and vector chunk metadata parity (`document_id`, `department_id`, `source`).
- Verify strict scope settings when answers are intentionally blocked due to low evidence.
