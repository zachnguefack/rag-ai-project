"""Production-oriented RAG toolkit."""

from .config import AppConfig, DEFAULT_CONFIG
from .data_loader import DocumentIngestionPipeline, IngestionReport
from .embeddings import EmbeddingManager
from .store import VectorStore
from .retrieval import RAGRetriever
from .answer import RAGService
from .smart_indexing import IndexStateStore, SmartIndexer

__all__ = [
    "AppConfig",
    "DEFAULT_CONFIG",
    "DocumentIngestionPipeline",
    "IngestionReport",
    "EmbeddingManager",
    "VectorStore",
    "RAGRetriever",
    "RAGService",
    "IndexStateStore",
    "SmartIndexer",
]
