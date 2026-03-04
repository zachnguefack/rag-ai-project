# RAG v2 - Production-oriented implementation

## What is included

- Robust multi-format ingestion pipeline with metadata normalization.
- Recursive chunking with language detection.
- OpenAI embedding manager with retries + persistent cache.
- Persistent ChromaDB vector store with stable chunk IDs.
- Incremental (smart) indexing using file fingerprints (mtime/size/hash).
- Hybrid retrieval ranking (semantic + lexical) + MMR diversification.
- Strict and balanced answer modes with graceful fallback.
- Structured logging and modular architecture.

## Quick start

```bash
pip install -e .
export OPENAI_API_KEY=your_key
```

### Index documents

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

### Ask questions

```python
from rag_v2 import RAGRetriever
from rag_v2.answer import RAGService, AnswerPolicy

retriever = RAGRetriever(store, emb)
service = RAGService(retriever)

result = service.answer("What are the onboarding steps?", policy=AnswerPolicy(mode="strict"))
print(result["answer"])
print(result["citations"])
```

## Design notes

- Use `strict` mode for enterprise use cases (no-doc => deterministic insufficient evidence).
- Use `balanced` mode for assistant behavior with controlled fallback.
- Keep chunk size/overlap and retrieval thresholds configurable based on benchmark data.
