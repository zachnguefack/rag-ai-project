# RAG v2 - Production-oriented implementation

## What is included

- Robust multi-format ingestion pipeline with metadata normalization.
- Recursive chunking with language detection.
- OpenAI embedding manager with retries + persistent cache.
- Persistent ChromaDB vector store with stable chunk IDs.
- Incremental (smart) indexing using file fingerprints (mtime/size/hash).
- Hybrid retrieval ranking (semantic + lexical) + MMR diversification.
- Strict and balanced answer modes with optional **Strict Document Scope** guard.
- Structured logging and modular architecture.

## Quick start

```bash
pip install -e .
export OPENAI_API_KEY=your_key
```

## Index documents

```python
from pathlib import Path

from rag_v2 import DocumentIngestionPipeline, EmbeddingManager, VectorStore
from rag_v2.smart_indexing import IndexStateStore, SmartIndexer

emb = EmbeddingManager()
store = VectorStore()
state = IndexStateStore(Path("data/vector_store/index_state.json"))

indexer = SmartIndexer(
    data_dir=Path("data"),
    ingestion_pipeline=DocumentIngestionPipeline(),
    embedding_manager=emb,
    vector_store=store,
    state_store=state,
    chunk_size=900,
    chunk_overlap=140,
)
summary = indexer.run(force_reindex=False)
print(summary)
```

## Ask questions

```python
from rag_v2 import RAGRetriever
from rag_v2.answer import AnswerPolicy, RAGService

retriever = RAGRetriever(store, emb)
service = RAGService(retriever)

result = service.answer(
    "What are the onboarding steps?",
    policy=AnswerPolicy(mode="balanced"),
)
print(result["answer"])
print(result["citations"])
```

## Strict Document Scope mode

When `strict_document_scope=True`, the system becomes **retrieval-gated**:

1. Retrieve and post-process chunks from the vector DB.
2. Validate retrieval evidence (`min_results` + `min_confidence`).
3. If evidence is insufficient, **do not call the LLM**.
4. Return a deterministic enterprise message:

> No relevant information was found in the available documentation.  
> Your question may be outside the scope of the company's knowledge base.  
> Please contact your administrator or the relevant department for further assistance.

This prevents hallucinated answers for out-of-scope queries.

### Python usage

```python
from rag_v2.answer import AnswerPolicy

policy = AnswerPolicy(
    mode="balanced",  # keep balanced style if evidence exists
    strict
    min_results=2,
    min_confidence=0.40,
)
result = service.answer("Question here", policy=policy)
```

### CLI usage

```bash
python main.py \
  --query "What is the VPN enrollment process?" \
  --mode balanced \
  --strict-document-scope
```

### Configuration options

`AppConfig` fields related to strict scope:

- `strict_document_scope` (bool, default `False`): Enable retrieval-gated strict document behavior globally.
- `strict_min_results` (int, default `2`): Minimum retrieved chunks required to consider a response grounded.
- `strict_min_confidence` (float, default `0.40`): Minimum confidence score required to proceed with generation.

## Design notes

- Use `strict_document_scope=True` for enterprise use cases that must avoid general-knowledge fallback.
- Use `balanced` mode with `strict_document_scope=False` for assistant behavior with controlled fallback.
- Keep chunk size/overlap and retrieval thresholds configurable based on benchmark data.


## FastAPI backend

A production-oriented backend is now available and wraps indexing + query operations in REST endpoints:

```bash
uvicorn rag_v2.backend:app --host 0.0.0.0 --port 8000
```

Available endpoints (prefix: `/api/v1`):
- `GET /health`
- `POST /index`
- `POST /query`

Authentication controls:
- Set `RAG_ALLOW_UNAUTHENTICATED=false` to require API key auth.
- Set `RAG_API_KEY=<your-secret>` and provide `x-api-key` header in protected calls.
- `POST /query` also requires `X-User-Id` and optional `X-User-Role` headers.

Document access control for retrieval:
- The query lifecycle is now: **authenticate request -> validate user role -> build document access filter -> vector retrieval -> answer generation**.
- Define ACL rules in `RAG_ACCESS_POLICY_PATH` (defaults to `data/access_policy.json`).
- ACL entries are applied as metadata filters before vector search so users only retrieve allowed documents.

## Enterprise FastAPI backend blueprint

For backend architecture and operations documentation, see:

- `docs/backend_developer_guide.md` (current implementation guide)
- `docs/rbac_backend.md` (RBAC and access-control details)
- `docs/enterprise_fastapi_backend_architecture.md` (reference architecture blueprint)
- `docs/backend_runtime_deployment.md` (runtime deployment notes)


## Backend RBAC administration in Swagger

The FastAPI backend exposes admin RBAC APIs under `/api/v1/admin` in the **Roles & Permissions** Swagger tag.

- Source of truth for role-permission mapping: `backend/app/security/policies.py`.
- Validation flow: identity (`X-User-Id` or Bearer token) -> decorators/permission checks -> optional document-level deny-by-default checks.
- Use `/api/v1/admin/rbac/matrix` to inspect the full RBAC matrix and `/api/v1/admin/rbac/validate` to test user permission outcomes.

Detailed usage and examples are documented in `docs/rbac_backend.md`.

## Department-based secure document access (updated)

The backend now enforces a department-aware access model with explicit grants:

- Users can be assigned to **multiple departments** (admin-managed).
- A user can retrieve documents from:
  1) all assigned departments, and
  2) documents explicitly granted to the user.
- Explicit revocation of per-document grants is supported.

Effective retrieval scope is computed in backend services **before** retrieval:

`authorized_document_ids = docs_in_assigned_departments UNION explicit_grants MINUS revoked_grants`

This scope is converted to a metadata filter and passed into retrieval, so unauthorized docs are never sent into the RAG pipeline.

### Admin APIs for access operations

All under `/api/v1/admin`:

- `POST /users/{user_id}/departments/{department_id}`
- `DELETE /users/{user_id}/departments/{department_id}`
- `GET /users/{user_id}/departments`
- `GET /departments/{department_id}/users`
- `POST /users/{user_id}/document-access`
- `GET /users/{user_id}/document-access`
- `DELETE /users/{user_id}/document-access/{document_id}`
- `GET /users/{user_id}/document-scope`

### Security notes

- Access filtering is backend-enforced (not frontend-only).
- Admin assignment endpoints require `MANAGE_USERS` permission.
- Retrieval also strips unauthorized citations as defense in depth.


### Retrieval scope parity and `indexed=true` semantics

- `GET /api/v1/documents` is metadata-registry scoped (SQLite document records + ACL scope).
- `POST /api/v1/chat/ask` and `POST /api/v1/rag/query` are vector-retrieval scoped and use the same ACL scope translated into vector metadata filters.
- For retrieval to work, vector chunks must include at least: `department_id`, `document_id`, and `source` metadata.
- `indexed=true` should be interpreted as: indexing job completed for the document version and chunks were expected to be persisted in the configured vector collection; retrieval can still fail if metadata mapping is inconsistent.

Common causes of `confidence.details.reason = "no_scores"`:
- Authorized scope exists in metadata DB, but chunk metadata is missing `document_id` or has a mismatched value.
- Retrieval filter uses a metadata key that does not exist in vector chunks (for example `source_path` vs `source`).
- Score threshold is too strict for the query/language/content.
- Document was marked indexed in registry but the expected collection has no chunks for that source.

- [Enterprise RAG persistence refactor](docs/enterprise_rag_persistence_refactor.md)
