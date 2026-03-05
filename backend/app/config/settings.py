from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rag_v2 import DEFAULT_CONFIG


@dataclass(slots=True)
class BackendSettings:
    app_name: str = "RAG v2 Backend"
    app_version: str = "1.0.0"
    app_env: str = os.getenv("APP_ENV", "development")

    api_key: str | None = os.getenv("RAG_API_KEY")
    allow_unauthenticated: bool = os.getenv("RAG_ALLOW_UNAUTHENTICATED", "true").lower() == "true"

    jwt_secret_key: str = os.getenv("RAG_JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    jwt_access_token_expire_minutes: int = int(os.getenv("RAG_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    data_dir: Path = DEFAULT_CONFIG.data_dir
    vector_store_dir: Path = DEFAULT_CONFIG.vector_store_dir
    embedding_cache_path: Path = DEFAULT_CONFIG.embedding_cache_path
    collection_name: str = DEFAULT_CONFIG.collection_name

    embedding_model: str = DEFAULT_CONFIG.embedding_model
    chat_model: str = DEFAULT_CONFIG.chat_model

    chunk_size: int = DEFAULT_CONFIG.chunk_size
    chunk_overlap: int = DEFAULT_CONFIG.chunk_overlap

    embedding_batch_size: int = DEFAULT_CONFIG.embedding_batch_size
    embedding_retry_max_attempts: int = DEFAULT_CONFIG.embedding_retry_max_attempts
    embedding_retry_base_wait_s: float = DEFAULT_CONFIG.embedding_retry_base_wait_s

    retrieval_top_k: int = DEFAULT_CONFIG.retrieval_top_k
    final_top_k: int = DEFAULT_CONFIG.final_top_k
    similarity_threshold: float = DEFAULT_CONFIG.similarity_threshold
    mmr_lambda: float = DEFAULT_CONFIG.mmr_lambda

    strict_min_results: int = DEFAULT_CONFIG.strict_min_results
    strict_min_confidence: float = DEFAULT_CONFIG.strict_min_confidence
    strict_document_scope: bool = DEFAULT_CONFIG.strict_document_scope


def load_settings() -> BackendSettings:
    return BackendSettings()
