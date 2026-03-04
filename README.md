# RAG v2 - Production-oriented implementation

## What is included

- Robust multi-format ingestion pipeline with metadata normalization.
- Recursive chunking with language detection.
- OpenAI embedding manager with retries + persistent cache.
- Persistent ChromaDB vector store with stable chunk IDs.
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
from rag_v2 import DocumentIngestionPipeline, EmbeddingManager, VectorStore
from rag_v2.indexing import index_documents

pipeline = DocumentIngestionPipeline()
docs, report = pipeline.load_documents("data")

emb = EmbeddingManager()
store = VectorStore(reset=True)
index_documents(docs, emb, store)
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
