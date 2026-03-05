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

## Enterprise FastAPI backend blueprint

For a production-ready enterprise backend architecture (API, security, RBAC, document management, RAG engine, vector DB, audit logging, and configuration management), see:

- `docs/enterprise_fastapi_backend_architecture.md`
