# Single-Tenant Enterprise RAG Architecture (Windows + Linux, No Docker)

## 1) Executive Architecture Proposal

This architecture targets **regulated enterprise environments** (banking/pharma/insurance) where each company runs an isolated stack.

- **Tenant model:** one company = one deployment unit (frontend + backend + DB + vector index + storage integrations).
- **Codebase model:** one shared codebase with environment-specific configuration.
- **OS model:** deployable on Windows Server and Linux.
- **Hosting model:** cloud or on-prem.
- **Container model:** no Docker required.

Primary design choices:

1. **BFF-style API boundary** with Next.js UI separated from FastAPI backend.
2. **Policy Enforcement Point (PEP)** in retrieval pipeline: document ACL filtering occurs before any vector search execution.
3. **Strict Document Scope mode** as an enforceable runtime policy (not just prompt text).
4. **SQL Server as system of record** for identity, metadata, ACL, jobs, audit.
5. **Pluggable adapters** for vector index, object storage, IdP/SSO, and SIEM export.

---

## 2) High-Level Component Diagram (Text)

```text
[User Browser]
    |
    v
[IIS (Windows) or Nginx (Linux)] ----> [Next.js static assets + SSR handler]
    |
    | /api/*
    v
[FastAPI Application Layer]
    |- AuthN Adapter (OIDC/SAML token validation)
    |- AuthZ/RBAC + Document ACL Policy Engine (PEP)
    |- RAG Orchestrator
    |- Admin API
    |- Audit Logger
    |- Health/Readiness
    |
    +--> [SQL Server]
    |      |- Users, Roles, Permissions
    |      |- Documents, Versions, ACL, Index state
    |      |- App config + Feature flags
    |      |- Audit logs
    |
    +--> [Document Storage Adapter]
    |      |- Local FS / NAS
    |      |- SharePoint
    |      |- S3-compatible
    |
    +--> [Vector Index Adapter]
    |      |- External managed service (Azure AI Search/Pinecone/etc.)
    |      |- Local persistent (Qdrant/Milvus/pgvector)
    |
    +--> [LLM/Embedding Provider Adapter]
    |
    +--> [Background Worker Service]
           |- Incremental indexing
           |- Re-index / repair jobs
           |- SIEM export job (optional)
```

---

## 3) Logical Layers & Separation of Concerns

1. **Presentation layer**
   - Next.js admin and end-user UI.
   - No direct DB access; all operations through backend APIs.

2. **API/Application layer (FastAPI)**
   - Request validation, authentication, authorization checks.
   - Orchestrates retrieval + generation workflows.

3. **Domain layer**
   - Entities and business rules: documents, versions, ACL inheritance, indexing state, strict-scope policy.

4. **Infrastructure layer**
   - SQL Server repositories.
   - Vector store connectors.
   - Storage connectors.
   - SIEM exporter.

5. **Worker/Job layer**
   - Incremental indexing and long-running tasks outside request path.

This keeps enterprise maintainability high: UI, API, domain rules, and infra adapters can evolve independently.

---

## 4) Backend Module Structure (Clean Architecture)

```text
backend/
  app/
    api/
      v1/
        auth.py
        admin_users.py
        admin_roles.py
        admin_documents.py
        admin_indexing.py
        admin_audit.py
        rag_query.py
        health.py
      deps.py
    application/
      commands/
      queries/
      services/
        rag_service.py
        acl_service.py
        indexing_service.py
        audit_service.py
    domain/
      entities/
      value_objects/
      policies/
        document_scope_policy.py
      events/
    infrastructure/
      persistence/
        sqlserver/
          models/
          repositories/
          uow.py
      vector_index/
        base.py
        qdrant_adapter.py
        azure_search_adapter.py
        pgvector_adapter.py
      storage/
        filesystem_adapter.py
        sharepoint_adapter.py
        s3_adapter.py
      identity/
        oidc_adapter.py
        saml_adapter.py
      siem/
        splunk_adapter.py
        sentinel_adapter.py
    workers/
      scheduler.py
      jobs/
        incremental_index_job.py
        reindex_job.py
        audit_export_job.py
    config/
      settings.py
      feature_flags.py
      secrets.py
```

---

## 5) Data Model Overview (SQL Server)

### Identity and RBAC

- `users`
  - `id (uniqueidentifier PK)`
  - `external_subject_id` (IdP user ID)
  - `username`, `email`, `status`, `last_login_at`, `created_at`
- `roles`
  - `id`, `name`, `description`, `is_system_role`
- `permissions`
  - `id`, `code` (e.g., `doc.read`, `doc.write`, `index.execute`, `audit.read`)
- `role_permissions`
  - `role_id`, `permission_id`
- `user_roles`
  - `user_id`, `role_id`, `scope_type`, `scope_id` (optional scoping)

### Document and Versioning

- `documents`
  - `id`, `external_key`, `title`, `owner_user_id`, `source_type`, `status`, `created_at`
- `document_versions`
  - `id`, `document_id`, `version_no`, `content_hash`, `storage_uri`, `mime_type`, `size_bytes`, `created_at`
- `document_metadata`
  - `document_id`, `key`, `value`
- `document_acl`
  - `id`, `document_id`, `principal_type` (`user`/`role`/`group`), `principal_id`, `access_level` (`read`/`write`/`admin`)

### Indexing and Retrieval State

- `index_jobs`
  - `id`, `job_type`, `triggered_by`, `status`, `started_at`, `finished_at`, `error_message`
- `document_index_state`
  - `document_version_id`, `index_backend`, `embedding_model`, `chunking_profile`, `indexed_at`, `index_status`, `last_error`
- `chunk_manifest`
  - `id`, `document_version_id`, `chunk_id`, `chunk_hash`, `token_count`, `vector_ref`, `acl_snapshot_hash`

### Configuration and Policy

- `app_config`
  - `key`, `value`, `updated_at`, `updated_by`
- `policy_config`
  - `strict_document_scope_enabled`, `min_evidence_chunks`, `confidence_threshold`, `deny_message_template`

### Audit

- `audit_log`
  - `id`, `timestamp_utc`, `actor_user_id`, `action`, `resource_type`, `resource_id`, `result`, `ip_address`, `correlation_id`, `details_json`

---

## 6) API Design (Key Endpoints)

### Auth and Session

- `GET /api/v1/auth/me`
- `POST /api/v1/auth/token/refresh`
- `POST /api/v1/auth/logout`

### Admin: Users / Roles / Permissions

- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users`
- `PUT /api/v1/admin/users/{id}/roles`
- `GET /api/v1/admin/roles`
- `POST /api/v1/admin/roles`
- `PUT /api/v1/admin/roles/{id}/permissions`

### Admin: Documents / ACL / Indexing

- `POST /api/v1/admin/documents`
- `POST /api/v1/admin/documents/{id}/versions`
- `PUT /api/v1/admin/documents/{id}/acl`
- `POST /api/v1/admin/index/jobs/incremental`
- `POST /api/v1/admin/index/jobs/reindex`
- `GET /api/v1/admin/index/jobs/{job_id}`

### RAG Query

- `POST /api/v1/rag/query`
  - Inputs: `query`, `conversation_id`, optional `document_filters`
  - Outputs: `answer`, `citations[]`, `policy_status`, `request_id`

### Audit & Operations

- `GET /api/v1/admin/audit`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/health/dependencies`

---

## 7) Security Model (Enterprise Controls)

## 7.1 Authentication / SSO

Recommended order:
1. OIDC with enterprise IdP (Azure AD/Entra, Okta, Keycloak).
2. SAML only where OIDC is not possible.

### 7.2 Authorization

- **RBAC** at endpoint/service level (`permission` checks).
- **Document ACL enforcement before retrieval**:
  1. Resolve user principals (user + groups + roles).
  2. Query SQL Server for authorized `document_id` set.
  3. Apply authorized IDs as hard filter in retrieval query.
  4. If authorized set is empty: deny retrieval.

### 7.3 Strict Document Scope (anti-hallucination policy)

When `strict_document_scope_enabled = true`:

1. Generation allowed only if minimum evidence threshold is met.
2. Prompt includes only retrieved authorized chunks.
3. If evidence is insufficient, return controlled policy response, e.g.:
   - “No authorized supporting documents were found for this query. Please refine your query or request access.”
4. Log policy decision in `audit_log`.

### 7.4 Audit and SIEM

- Every sensitive event is immutable and timestamped.
- Include user, action, target resource, outcome, and correlation ID.
- Optional near-real-time export connector to SIEM.

---

## 8) Incremental Indexing & Reliability

### Incremental indexing strategy

- Compute `content_hash` per document version.
- Index only when:
  - new version detected,
  - metadata impacting retrieval changed,
  - ACL changed (refresh ACL snapshot/hash),
  - embedding/chunk profile changed.
- Track state in `document_index_state`.

### Reliability patterns

- Idempotent job execution (job keys + safe retries).
- Dead-letter handling for failed jobs.
- Health checks:
  - liveness: process up,
  - readiness: SQL + vector + storage connectivity,
  - dependencies: detailed status for admins.
- Structured JSON logging with request correlation IDs.

---

## 9) Deployment Plan (No Docker)

## 9.1 Windows deployment (IIS + Windows Services)

1. **Provision host**
   - Windows Server (hardened baseline), IIS installed, URL Rewrite + ARR if needed.
2. **Frontend**
   - Build Next.js (`next build`).
   - Host via IIS site (static export or Node handler through iisnode/reverse proxy pattern).
3. **Backend API**
   - Python virtualenv.
   - Run FastAPI with `uvicorn` or `gunicorn` equivalent for Windows (e.g., `uvicorn --workers N`).
   - Register as Windows Service using NSSM or `sc create` wrapper.
4. **Reverse proxy**
   - IIS routes `/api/*` to FastAPI service port.
   - TLS termination and optional mTLS internally.
5. **Background worker**
   - Separate Windows Service for indexing jobs.
6. **Operations**
   - Event Viewer + file/central logging.
   - Scheduled backup scripts for config and app artifacts.

## 9.2 Linux deployment (Nginx + systemd)

1. **Provision host**
   - Hardened Linux VM, Nginx, Python runtime, Node runtime.
2. **Frontend**
   - `next build` and run production server or serve exported assets.
   - Nginx serves static assets and proxies dynamic routes.
3. **Backend API**
   - Python virtualenv + `uvicorn`/`gunicorn`.
   - systemd unit: `rag-api.service`.
4. **Worker**
   - systemd unit: `rag-worker.service`.
5. **Reverse proxy + TLS**
   - Nginx `/api/*` to FastAPI upstream.
6. **Operations**
   - journald + centralized logs (ELK/Splunk/etc.).

---

## 10) Configuration, Secrets, Migrations, Upgrades

### Configuration strategy

- Layered configuration:
  1. `appsettings` / `.env` for non-secret settings,
  2. environment variables for deploy-time overrides,
  3. secrets manager for credentials/keys.
- Environment profiles: `dev`, `qa`, `prod`.
- Per-tenant deployment has its own config package.

### Secrets management options

- On-prem: HashiCorp Vault or Windows DPAPI-backed secrets.
- Cloud: Azure Key Vault / AWS Secrets Manager.

### DB migrations

- Use Alembic (SQL Server dialect).
- Pipeline:
  1. backup DB,
  2. run migration scripts,
  3. run smoke tests,
  4. mark schema version in `alembic_version`.
- Enforce backward-compatible migration policy for zero/low downtime.

### Upgrade strategy

- Versioned release bundles per tenant (`frontend`, `backend`, `migrations`).
- Blue/green or rolling replacement where possible.
- Include rollback scripts and schema compatibility matrix.

---

## 11) Vector Index Options and Tradeoffs

### Option A: External managed service
Examples: Azure AI Search, Pinecone, Weaviate Cloud.

**Pros**
- Lower ops burden.
- Built-in scaling/HA.
- Faster time-to-production.

**Cons**
- Data residency/compliance constraints.
- Higher recurring cost.
- Vendor lock-in risks.

Best for: cloud-first organizations with strong managed-service governance.

### Option B: Local persistent vector store
Examples: Qdrant self-hosted, Milvus, pgvector in SQL ecosystem.

**Pros**
- Full control and on-prem compatibility.
- Easier sovereignty/compliance narratives.
- Predictable infra placement.

**Cons**
- Operational complexity (backup, HA, tuning).
- Capacity planning on your team.

Best for: strict on-prem/regulatory environments.

### Recommendation

- Default enterprise baseline: **Qdrant self-hosted** for on-prem and **managed vector service** for cloud deployments.
- Keep a strict adapter interface so migration between backends is possible without changing domain/application logic.

---

## 12) Document Storage Options and Tradeoffs

### Filesystem/NAS
- Pros: simple, on-prem friendly.
- Cons: access control and lifecycle tooling can be weaker.

### SharePoint
- Pros: enterprise-native, governance integration.
- Cons: API complexity and throttling considerations.

### S3-compatible
- Pros: scalable object lifecycle/versioning.
- Cons: requires object-storage operations maturity on-prem.

### Recommendation

- Start with **filesystem/NAS** for early on-prem implementations when speed matters.
- Move to **SharePoint or S3-compatible** where governance, lifecycle, and scale requirements increase.
- Always persist canonical metadata and ACL references in SQL Server.

---

## 13) SSO Options and Tradeoffs

### OIDC (recommended)
- Modern protocol, good developer ergonomics, robust token model.

### SAML
- Often required in legacy enterprise IAM landscapes.
- More integration overhead and less API-native than OIDC.

### Recommendation

- Implement OIDC first-class.
- Maintain SAML adapter for customers with hard constraints.
- Map external group claims to internal roles via deterministic policy rules.

---

## 14) Final Architecture Recommendation

For your stated requirements, the best professional approach is:

1. **Single-tenant deployment blueprint** with parameterized config and release automation.
2. **FastAPI backend with clean architecture** and strict policy enforcement points.
3. **SQL Server as authoritative control plane** (IAM, ACL, metadata, audit, indexing state).
4. **Pluggable vector + storage adapters** to support both cloud and on-prem without code forks.
5. **Strict Document Scope as hard runtime guardrail** with deterministic abstention behavior.
6. **Windows IIS + Services and Linux Nginx + systemd** as first-class deployment targets.

This provides compliance alignment, operational traceability, and portability while preserving long-term maintainability.
