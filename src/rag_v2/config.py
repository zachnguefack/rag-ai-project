from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class AppConfig:
    data_dir: Path = Path("data")
    vector_store_dir: Path = Path("data/vector_store")
    embedding_cache_path: Path = Path("data/cache/embeddings.jsonl")
    collection_name: str = "rag_v2_docs"

    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4.1-mini"

    chunk_size: int = 900
    chunk_overlap: int = 140

    embedding_batch_size: int = 96
    embedding_retry_max_attempts: int = 5
    embedding_retry_base_wait_s: float = 0.35

    retrieval_top_k: int = 20
    final_top_k: int = 6
    similarity_threshold: float = 0.25
    mmr_lambda: float = 0.75

    strict_min_results: int = 2
    strict_min_confidence: float = 0.40


DEFAULT_CONFIG = AppConfig()
