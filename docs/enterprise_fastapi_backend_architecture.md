# Enterprise RAG Backend Architecture (FastAPI)

This document proposes a production-ready backend architecture for an enterprise Retrieval-Augmented Generation (RAG) platform implemented with **Python + FastAPI**.

## 1) Architecture goals

- Clean separation of concerns and domain boundaries.
- Security-by-default (authentication, RBAC, auditability).
- Scalable RAG pipeline with independent ingestion/retrieval services.
- Provider-agnostic vector database and LLM integrations.
- Operational readiness (configuration, observability, background workers).

## 2) High-level component view

```text
Clients (Web, API consumers, internal tools)
  -> API Gateway / FastAPI Routers
    -> AuthN + AuthZ (JWT/OIDC + RBAC)
      -> Application Services
        -> Document Management
        -> RAG Orchestration
        -> Audit Service
        -> Config Service
          -> Database (PostgreSQL)
          -> Vector DB (Qdrant/pgvector/Weaviate)
          -> Object Storage (S3/Azure Blob/GCS)
          -> Message Queue/Workers (Celery/RQ)
          -> LLM/Embedding Providers
```

## 3) Production-ready folder structure

```text
backend/
├── app/
│   ├── main.py                          # FastAPI app creation + middleware + startup
│   ├── api/                             # API layer
│   │   ├── deps.py                      # Shared request dependencies (db session, tenant, user)
│   │   ├── v1/
│   │   │   ├── router.py                # v1 API aggregator
│   │   │   ├── auth.py                  # Login, token refresh, OIDC callbacks
│   │   │   ├── users.py                 # User/account management endpoints
│   │   │   ├── documents.py             # Upload/list/delete/version documents
│   │   │   ├── retrieval.py             # Search/retrieve endpoints
│   │   │   ├── chat.py                  # Ask/answer RAG endpoints
│   │   │   ├── admin.py                 # Operational/admin endpoints
│   │   │   └── health.py                # Liveness/readiness/version endpoints
│   ├── services/                        # Business use cases (application layer)
│   │   ├── auth_service.py              # Token issuance, session policy, identity mapping
│   │   ├── rbac_service.py              # Permission evaluation and role resolution
│   │   ├── document_service.py          # Document lifecycle + metadata policy
│   │   ├── ingestion_service.py         # Parse/chunk/embed/index orchestration
│   │   ├── retrieval_service.py         # Hybrid search + reranking + filters
│   │   ├── rag_service.py               # End-to-end RAG orchestration and answer policy
│   │   ├── audit_service.py             # Structured immutable audit events
│   │   └── config_service.py            # Runtime config feature flags + tenant config
│   ├── models/                          # Domain and transfer models
│   │   ├── domain/
│   │   │   ├── user.py                  # Domain entities and invariants
│   │   │   ├── role.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── query.py
│   │   │   └── audit_event.py
│   │   ├── schema/                      # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── document.py
│   │   │   ├── retrieval.py
│   │   │   ├── chat.py
│   │   │   └── common.py
│   │   └── persistence/                 # SQLAlchemy ORM models
│   │       ├── user.py
│   │       ├── role.py
│   │       ├── permission.py
│   │       ├── document.py
│   │       ├── ingest_job.py
│   │       └── audit_log.py
│   ├── security/                        # Security module
│   │   ├── jwt.py                       # Access/refresh token handling
│   │   ├── password.py                  # Hashing policy (Argon2/Bcrypt)
│   │   ├── oauth2.py                    # OIDC/OAuth2 integration
│   │   ├── rbac.py                      # Declarative permission checks
│   │   ├── policies.py                  # Resource-level authorization policies
│   │   └── middleware.py                # Security headers, request context, rate limits
│   ├── database/                        # Database module
│   │   ├── session.py                   # SQLAlchemy engine/session management
│   │   ├── base.py                      # Declarative base metadata
│   │   ├── migrations/                  # Alembic scripts
│   │   ├── repositories/                # Data access abstractions
│   │   │   ├── user_repo.py
│   │   │   ├── role_repo.py
│   │   │   ├── document_repo.py
│   │   │   ├── ingest_job_repo.py
│   │   │   └── audit_repo.py
│   │   └── unit_of_work.py              # Transaction boundaries
│   ├── rag_engine/                      # RAG engine module
│   │   ├── providers/
│   │   │   ├── llm_provider.py          # LLM abstraction interface
│   │   │   ├── embedding_provider.py    # Embedding abstraction interface
│   │   │   └── reranker_provider.py     # Optional reranker abstraction
│   │   ├── ingestion/
│   │   │   ├── loaders.py               # PDF/DOCX/HTML/etc. loaders
│   │   │   ├── cleaners.py              # Text normalization and PII scrubbing hooks
│   │   │   ├── chunkers.py              # Chunking strategies
│   │   │   └── pipeline.py              # Ingestion pipeline orchestration
│   │   ├── retrieval/
│   │   │   ├── vector_retriever.py      # Dense retrieval
│   │   │   ├── keyword_retriever.py     # BM25/lexical retrieval
│   │   │   ├── hybrid.py                # Fusion/ranking strategy
│   │   │   └── filters.py               # Metadata/tenant/security filters
│   │   ├── generation/
│   │   │   ├── prompts.py               # Prompt templates and guardrails
│   │   │   ├── answer_builder.py        # Citation + answer construction
│   │   │   └── grounding.py             # Evidence thresholds / abstention policies
│   │   └── vector_store/
│   │       ├── interface.py             # VectorStore protocol
│   │       ├── qdrant_store.py          # Qdrant implementation
│   │       ├── pgvector_store.py        # pgvector implementation
│   │       └── factory.py               # Runtime backend selection
│   ├── workers/                          # Async/background processing
│   │   ├── celery_app.py
│   │   ├── tasks_ingestion.py
│   │   ├── tasks_reindex.py
│   │   └── tasks_audit_export.py
│   ├── observability/
│   │   ├── logging.py                   # Structured logs (JSON)
│   │   ├── tracing.py                   # OpenTelemetry setup
│   │   ├── metrics.py                   # Prometheus counters/histograms
│   │   └── audit.py                     # Audit event publishers
│   ├── config/                           # Configuration management
│   │   ├── settings.py                  # Pydantic settings + environment mapping
│   │   ├── feature_flags.py             # Feature toggles
│   │   └── secrets.py                   # Secret manager adapters
│   ├── common/
│   │   ├── exceptions.py
│   │   ├── constants.py
│   │   ├── enums.py
│   │   └── utils.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/
├── scripts/                              # Ops scripts (bootstrap, backfill, reindex)
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── k8s/
│   └── helm/
└── pyproject.toml
```

## 4) Module responsibilities (by required separation)

### API layer (`app/api`)
- Exposes versioned REST endpoints and OpenAPI contracts.
- Performs input validation, pagination, and request shaping.
- Delegates all business logic to `services` (no domain logic in routers).

### Services (`app/services`)
- Implements use-case orchestration for authentication, document workflows, and RAG operations.
- Coordinates repositories, security checks, and rag-engine components.
- Encapsulates transactional boundaries and idempotency behavior.

### Models (`app/models`)
- `domain`: core business entities and invariants.
- `schema`: external API contracts (Pydantic).
- `persistence`: ORM mappings for relational storage.

### Security (`app/security`)
- Authentication: OAuth2/OIDC + JWT validation and session policy.
- Authorization: RBAC and resource-level policy enforcement.
- Security middleware: headers, request identity propagation, optional rate limits.

### Database (`app/database`)
- SQL session and migration management.
- Repository pattern for aggregate reads/writes.
- Unit-of-work abstraction for safe commits/rollbacks.

### RAG engine (`app/rag_engine`)
- Ingestion: parsing, cleaning, chunking, embeddings.
- Retrieval: vector + keyword + hybrid ranking.
- Generation: prompting, grounding checks, citation-rich answer synthesis.
- Vector store abstraction for easy backend replacement.

## 5) Core cross-cutting systems

### Authentication system
- Preferred: enterprise IdP via OIDC (Azure AD/Okta/Keycloak).
- Access token for API calls; refresh token for long-lived sessions.
- Service-to-service auth via client credentials.

### RBAC
- Entities: users, roles, permissions, role bindings.
- API dependencies enforce `require_permission("document:read")` style checks.
- Support resource-scoped checks (tenant/project/document).

### Document management
- Upload files to object storage with immutable version IDs.
- Persist metadata in SQL (owner, tenant, tags, retention policy).
- Trigger async ingestion jobs and track status in `ingest_job` table.

### Vector database access
- `VectorStore` interface isolates vendor-specific code.
- Store embeddings with metadata: tenant_id, document_id, ACL tags, version.
- Enforce metadata filters for tenant isolation at retrieval time.

### Audit logging
- Emit append-only events for auth, document operations, and query/answer actions.
- Include actor, timestamp, action, resource, correlation_id, and outcome.
- Sink to SQL + optional SIEM export.

### Configuration management
- 12-factor config via environment variables + secret manager.
- Strongly typed settings (`Pydantic BaseSettings`).
- Feature flags for staged rollout (e.g., reranker on/off).

## 6) Recommended request lifecycle (query endpoint)

1. API receives `/v1/chat/ask` request.
2. Auth middleware validates token and request context.
3. RBAC verifies `rag:query` permission for tenant scope.
4. `rag_service` executes retrieval and grounding policy.
5. `rag_engine` generates answer with citations.
6. Response returned with trace ID.
7. `audit_service` stores query/answer audit event.

## 7) Scalability and reliability recommendations

- Stateless API pods behind load balancer.
- Dedicated worker pool for ingestion/reindex.
- DB read replicas for heavy metadata reads.
- Vector DB sharding/replication for large corpora.
- Caching layer (Redis) for session and hot query acceleration.
- Circuit breakers/retries/timeouts around LLM and vector providers.
- Full observability: structured logs, metrics, distributed tracing.
