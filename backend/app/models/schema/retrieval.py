from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=2)
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$")
    strict_document_scope: bool | None = None


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence_score: float
