# Backend implementation

This folder contains the FastAPI enterprise backend implementation derived from `docs/enterprise_fastapi_backend_architecture.md`.

## API to RAG flow example

1. `POST /v1/chat/ask` with bearer token and question.
2. Router validates auth and `rag:query` permission.
3. `RAGService` calls `HybridRetriever` (vector + keyword).
4. `AnswerBuilder` generates a grounded answer and citations are returned.

## Module guide

- `app/api`: routers + request dependencies.
- `app/services`: orchestration/business logic.
- `app/models`: domain/schema/persistence models.
- `app/security`: auth, JWT, RBAC, policies, middleware.
- `app/database`: session, unit-of-work, repositories.
- `app/rag_engine`: ingestion/retrieval/generation/vector-store interfaces.
- `app/workers`: async/background task entrypoints.
- `app/observability`: logging, tracing, metrics, audit hooks.
