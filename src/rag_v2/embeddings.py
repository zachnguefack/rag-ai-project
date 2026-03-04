from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

LOGGER = logging.getLogger("rag_v2.embeddings")


class EmbeddingManager:
    """Embedding manager with batching, retries and file-backed cache."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        cache_path: str | Path = "data/cache/embeddings.jsonl",
        batch_size: int = 96,
        max_retries: int = 5,
        base_wait_s: float = 0.35,
    ):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required")

        self.model_name = model_name
        self.model = OpenAIEmbeddings(model=model_name, api_key=api_key)
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.base_wait_s = base_wait_s
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        self._cache = self._load_cache(self.cache_path)
        self.dim = len(self.model.embed_query("dimension probe"))
        LOGGER.info("Embedding model initialized model=%s dim=%s cache_items=%s", self.model_name, self.dim, len(self._cache))

    @staticmethod
    def _hash_text(text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _load_cache(path: Path) -> Dict[str, List[float]]:
        if not path.exists():
            return {}
        cache: Dict[str, List[float]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
                cache[obj["h"]] = obj["v"]
            except Exception:
                continue
        return cache

    def _append_cache(self, rows: Sequence[tuple[str, List[float]]]) -> None:
        with self.cache_path.open("a", encoding="utf-8") as fh:
            for h, vec in rows:
                fh.write(json.dumps({"h": h, "v": vec}, ensure_ascii=False) + "\n")

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        vectors: List[List[float] | None] = [None] * len(texts)
        missing_texts: List[str] = []
        missing_idx: List[int] = []

        for i, text in enumerate(texts):
            h = self._hash_text(text)
            if h in self._cache:
                vectors[i] = self._cache[h]
            else:
                missing_texts.append(text)
                missing_idx.append(i)

        new_rows: List[tuple[str, List[float]]] = []
        for start in range(0, len(missing_texts), self.batch_size):
            batch = missing_texts[start : start + self.batch_size]
            embedded_batch: List[List[float]] | None = None

            for attempt in range(1, self.max_retries + 1):
                try:
                    embedded_batch = self.model.embed_documents(batch)
                    break
                except Exception as exc:
                    if attempt == self.max_retries:
                        LOGGER.exception("Embedding batch failed after retries start=%s size=%s", start, len(batch))
                        raise
                    wait = self.base_wait_s * (2 ** (attempt - 1))
                    LOGGER.warning("Embedding retry attempt=%s wait=%.2fs err=%s", attempt, wait, exc)
                    time.sleep(wait)

            assert embedded_batch is not None
            for idx_in_batch, vec in enumerate(embedded_batch):
                text = batch[idx_in_batch]
                h = self._hash_text(text)
                new_rows.append((h, vec))

        for i, text_i in zip(missing_idx, missing_texts):
            h = self._hash_text(text_i)
            vectors[i] = dict(new_rows)[h]

        if new_rows:
            for h, vec in new_rows:
                self._cache[h] = vec
            self._append_cache(new_rows)

        return np.asarray(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not query.strip():
            return np.zeros((self.dim,), dtype=np.float32)
        return np.asarray(self.model.embed_query(query), dtype=np.float32)
