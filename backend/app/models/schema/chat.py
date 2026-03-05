from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["Summarize the leave policy."])
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$", examples=["strict"])
    strict_document_scope: bool | None = Field(default=None, examples=[False])


class QueryResponse(BaseModel):
    answer: str
    mode: str
    source_type: str
    doc_grounded: bool
    confidence: dict
    citations: list[str]
