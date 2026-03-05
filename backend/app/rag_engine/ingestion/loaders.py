from __future__ import annotations

from rag_v2 import DocumentIngestionPipeline


def build_loader_pipeline() -> DocumentIngestionPipeline:
    return DocumentIngestionPipeline()
