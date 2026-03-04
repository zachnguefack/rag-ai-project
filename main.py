from __future__ import annotations

import argparse
import logging
from pathlib import Path

from rag_v2 import DEFAULT_CONFIG, DocumentIngestionPipeline, EmbeddingManager, RAGRetriever, RAGService, SmartIndexer, VectorStore
from rag_v2.answer import AnswerPolicy
from rag_v2.smart_indexing import IndexStateStore


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for indexing and query execution."""
    parser = argparse.ArgumentParser(description="RAG v2 incremental indexing and QA pipeline")
    parser.add_argument("--query", type=str, default="", help="Question to ask after indexing")
    parser.add_argument("--mode", choices=["strict", "balanced"], default="balanced", help="Answer generation mode")
    parser.add_argument("--force-reindex", action="store_true", help="Rebuild the full index regardless of file changes")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_CONFIG.data_dir, help="Directory containing source documents")
    parser.add_argument(
        "--strict-document-scope",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_CONFIG.strict_document_scope,
        help="Enable/disable document-only answering when retrieval evidence is weak",
    )
    return parser


def main() -> None:
    """Run smart indexing, then execute retrieval + generation for an optional query."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    args = build_parser().parse_args()

    config = DEFAULT_CONFIG
    data_dir = Path(args.data_dir)

    ingestion_pipeline = DocumentIngestionPipeline()
    embedding_manager = EmbeddingManager(
        model_name=config.embedding_model,
        cache_path=config.embedding_cache_path,
        batch_size=config.embedding_batch_size,
        max_retries=config.embedding_retry_max_attempts,
        base_wait_s=config.embedding_retry_base_wait_s,
    )
    vector_store = VectorStore(collection_name=config.collection_name, persist_directory=str(config.vector_store_dir))

    state_store = IndexStateStore(config.vector_store_dir / "index_state.json")
    indexer = SmartIndexer(
        data_dir=data_dir,
        ingestion_pipeline=ingestion_pipeline,
        embedding_manager=embedding_manager,
        vector_store=vector_store,
        state_store=state_store,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    summary = indexer.run(force_reindex=args.force_reindex)
    print(
        f"Indexing summary: files={summary.indexed_files}, chunks={summary.indexed_chunks}, "
        f"removed={summary.removed_files}, reused_existing={summary.reused_existing_index}"
    )

    if not args.query.strip():
        return

    retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedding_manager)
    service = RAGService(retriever=retriever, model=config.chat_model)
    result = service.answer(
        question=args.query,
        policy=AnswerPolicy(
            mode=args.mode,
            top_k_retrieve=config.retrieval_top_k,
            final_k=config.final_top_k,
            score_threshold=config.similarity_threshold,
            lambda_mult=config.mmr_lambda,
            min_results=config.strict_min_results,
            min_confidence=config.strict_min_confidence,
            strict_document_scope=args.strict_document_scope,
        ),
    )

    print("\nAnswer:\n")
    print(result["answer"])
    if result.get("citations"):
        print("\nCitations:")
        for citation in result["citations"]:
            print(citation)


if __name__ == "__main__":
    main()
