from __future__ import annotations

import threading
from typing import Any

from rag_v2 import EmbeddingManager, RAGRetriever, RAGService, SmartIndexer
from rag_v2.answer import AnswerPolicy
from rag_v2.smart_indexing import IndexStateStore

from app.config.settings import BackendSettings
from app.rag_engine.ingestion.pipeline import build_ingestion_pipeline
from app.rag_engine.vector_store.factory import build_vector_store


class RAGApplicationService:
    def __init__(self, settings: BackendSettings):
        self._settings = settings
        self._lock = threading.Lock()

        self._ingestion_pipeline = build_ingestion_pipeline()
        self._embedding_manager = EmbeddingManager(
            model_name=settings.embedding_model,
            cache_path=settings.embedding_cache_path,
            batch_size=settings.embedding_batch_size,
            max_retries=settings.embedding_retry_max_attempts,
            base_wait_s=settings.embedding_retry_base_wait_s,
        )
        self._vector_store = build_vector_store(
            collection_name=settings.collection_name,
            persist_directory=str(settings.vector_store_dir),
        )
        self._state_store = IndexStateStore(settings.vector_store_dir / "index_state.json")
        self._indexer = SmartIndexer(
            data_dir=settings.data_dir,
            ingestion_pipeline=self._ingestion_pipeline,
            embedding_manager=self._embedding_manager,
            vector_store=self._vector_store,
            state_store=self._state_store,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        retriever = RAGRetriever(vector_store=self._vector_store, embedding_manager=self._embedding_manager)
        self._rag_service = RAGService(retriever=retriever, model=settings.chat_model)

    def run_indexing(self, force_reindex: bool) -> dict:
        with self._lock:
            summary = self._indexer.run(force_reindex=force_reindex)

        return {
            "indexed_files": summary.indexed_files,
            "indexed_chunks": summary.indexed_chunks,
            "removed_files": summary.removed_files,
            "reused_existing_index": summary.reused_existing_index,
        }

    def answer(
        self,
        question: str,
        mode: str,
        strict_document_scope: bool | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict:
        strict_scope = self._settings.strict_document_scope if strict_document_scope is None else strict_document_scope

        policy = AnswerPolicy(
            mode=mode,
            top_k_retrieve=self._settings.retrieval_top_k,
            final_k=self._settings.final_top_k,
            score_threshold=self._settings.similarity_threshold,
            lambda_mult=self._settings.mmr_lambda,
            min_results=self._settings.strict_min_results,
            min_confidence=self._settings.strict_min_confidence,
            strict_document_scope=strict_scope,
        )
        response = self._rag_service.answer(question=question, policy=policy, metadata_filter=metadata_filter)
        response["citations"] = [str(citation) for citation in response.get("citations", [])]
        return response
