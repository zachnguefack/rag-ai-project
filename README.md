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
    strict_document_scope=True,
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

For a production-ready enterprise backend architecture (API, security, RBAC, document management, RAG engine, vector DB, audit logging, and configuration management), see:

- `docs/enterprise_fastapi_backend_architecture.md`

- `docs/backend_runtime_deployment.md`


## Backend RBAC administration in Swagger

The FastAPI backend exposes admin RBAC APIs under `/api/v1/admin` in the **Roles & Permissions** Swagger tag.

- Source of truth for role-permission mapping: `backend/app/security/policies.py`.
- Validation flow: identity (`X-User-Id` or Bearer token) -> decorators/permission checks -> optional document-level deny-by-default checks.
- Use `/api/v1/admin/rbac/matrix` to inspect the full RBAC matrix and `/api/v1/admin/rbac/validate` to test user permission outcomes.

Detailed usage and examples are documented in `docs/rbac_backend.md`.
