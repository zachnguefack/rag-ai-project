from __future__ import annotations

import os
import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


class EmbeddingManager:
    """OpenAI embeddings wrapper with consistent API."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        load_dotenv()
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        if not os.environ["OPENAI_API_KEY"]:
            raise RuntimeError("OPENAI_API_KEY is missing. Put it in your .env file.")

        self.model_name = model_name
        self.model = OpenAIEmbeddings(model=self.model_name)

        dim_probe = self.model.embed_query("dimension probe")
        self.dim = len(dim_probe)
        print(f"[EmbeddingManager] Model={self.model_name} | dim={self.dim}")

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        vecs = self.model.embed_documents(texts)
        return np.asarray(vecs, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not query:
            return np.zeros((self.dim,), dtype=np.float32)
        v = self.model.embed_query(query)
        return np.asarray(v, dtype=np.float32)