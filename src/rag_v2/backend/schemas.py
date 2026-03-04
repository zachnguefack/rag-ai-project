from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class IndexRequest(BaseModel):
    force_reindex: bool = False


class IndexResponse(BaseModel):
    indexed_files: int
    indexed_chunks: int
    removed_files: int
    reused_existing_index: bool


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2)
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$")
    strict_document_scope: bool | None = None


class QueryResponse(BaseModel):
    answer: str
    mode: str
    source_type: str
    doc_grounded: bool
    confidence: dict
    citations: list[str]
