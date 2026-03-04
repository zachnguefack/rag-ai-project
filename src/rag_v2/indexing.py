from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .embeddings import EmbeddingManager
from .store import VectorStore
from .text import prepare_chunks, assign_chunk_index_per_page


@dataclass
class EmbeddingConfig:
    batch_size: int = 128
    sleep_s: float = 0.25
    max_retries: int = 5
    use_cache: bool = True
    cache_path: Path = Path("data/emb_cache_text-embedding-3-small.jsonl")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache(path: Path) -> Dict[str, List[float]]:
    cache: Dict[str, List[float]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            obj = json.loads(line)
            cache[obj["h"]] = obj["v"]
    return cache


def _append_cache(path: Path, items: List[Tuple[str, List[float]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for h, v in items:
            f.write(json.dumps({"h": h, "v": v}) + "\n")


def generate_embeddings_batched(
    embedding_manager: EmbeddingManager,
    texts: List[str],
    cfg: EmbeddingConfig,
) -> np.ndarray:
    if not texts:
        return np.empty((0, embedding_manager.dim), dtype=np.float32)

    cache: Dict[str, List[float]] = _load_cache(cfg.cache_path) if cfg.use_cache else {}
    vectors: List[Optional[List[float]]] = [None] * len(texts)

    missing_texts: List[str] = []
    missing_idx: List[int] = []

    for i, t in enumerate(texts):
        h = _hash_text(t)
        if cfg.use_cache and h in cache:
            vectors[i] = cache[h]
        else:
            missing_texts.append(t)
            missing_idx.append(i)

    if missing_texts:
        new_vectors_flat: List[List[float]] = []

        for start in range(0, len(missing_texts), cfg.batch_size):
            batch = missing_texts[start : start + cfg.batch_size]

            for attempt in range(1, cfg.max_retries + 1):
                try:
                    batch_arr = embedding_manager.embed_documents(batch)
                    new_vectors_flat.extend(batch_arr.tolist())
                    break
                except Exception as e:
                    if attempt == cfg.max_retries:
                        raise
                    wait = cfg.sleep_s * (2 ** (attempt - 1))
                    print(f"[Embeddings] batch {start}-{start+len(batch)} failed (attempt {attempt}): {e}")
                    print(f"[Embeddings] retrying in {wait:.1f}s...")
                    time.sleep(wait)

            time.sleep(cfg.sleep_s)

        to_cache: List[Tuple[str, List[float]]] = []
        for t, v, i in zip(missing_texts, new_vectors_flat, missing_idx):
            vectors[i] = v
            if cfg.use_cache:
                to_cache.append((_hash_text(t), v))

        if cfg.use_cache and to_cache:
            _append_cache(cfg.cache_path, to_cache)

    return np.asarray(vectors, dtype=np.float32)


def embed_and_store_chunks(
    chunks: List[Any],
    embedding_manager: EmbeddingManager,
    vectorstore: VectorStore,
    cfg: EmbeddingConfig | None = None,
) -> None:
    cfg = cfg or EmbeddingConfig()

    filtered_chunks, texts = prepare_chunks(chunks)
    if not filtered_chunks:
        print("[Pipeline] No valid chunks.")
        return

    filtered_chunks = assign_chunk_index_per_page(filtered_chunks)

    embeddings = generate_embeddings_batched(embedding_manager, texts, cfg)
    if embeddings.shape[0] != len(filtered_chunks):
        raise RuntimeError("Embeddings/texts/chunks misalignment.")

    vectorstore.add_documents(filtered_chunks, embeddings)