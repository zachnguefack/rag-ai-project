from __future__ import annotations

import threading
from typing import Any

from rag_v2 import EmbeddingManager, RAGService, SmartIndexer, VectorStore
from rag_v2.answer import AnswerPolicy
from rag_v2.smart_indexing import IndexStateStore

from app.config.settings import BackendSettings
from app.models.domain.user import User
from app.rag_engine.ingestion.pipeline import build_ingestion_pipeline
from app.services.secure_retriever_service import SecureRetriever
from app.services.scope_builder_service import ScopeBuilderService

ENTERPRISE_SCOPE_BLOCK_MESSAGE = (
    "No relevant information was found in the available authorized documentation.\n"
    "Your question may be outside the scope of the documentation assigned to you.\n"
    "Please contact your administrator or the relevant department for further assistance."
)


class RAGApplicationService:
    def __init__(self, settings: BackendSettings, scope_builder: ScopeBuilderService):
        self._settings = settings
        self._scope_builder = scope_builder
        self._lock = threading.Lock()

        self._ingestion_pipeline = build_ingestion_pipeline()
        self._embedding_manager = EmbeddingManager(
            model_name=settings.embedding_model,
            cache_path=settings.embedding_cache_path,
            batch_size=settings.embedding_batch_size,
            max_retries=settings.embedding_retry_max_attempts,
            base_wait_s=settings.embedding_retry_base_wait_s,
        )
        self._vector_store = VectorStore(
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

        secure_retriever = SecureRetriever(
            vector_store=self._vector_store,
            embedding_manager=self._embedding_manager,
            scope_builder=scope_builder,
        )
        self._secure_retriever = secure_retriever
        self._rag_service = RAGService(retriever=secure_retriever, model=settings.chat_model)

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
        *,
        user: User,
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
            no_relevant_docs_message=ENTERPRISE_SCOPE_BLOCK_MESSAGE,
        )
        scope = self._scope_builder.build_scope(user)
        response = self._rag_service.answer(
            question=question,
            policy=policy,
            metadata_filter=metadata_filter,
            user=user,
        )
        response["citations"] = [str(citation) for citation in response.get("citations", [])]
        response["authorized_document_ids_count"] = len(scope.authorized_document_ids)
        return response
