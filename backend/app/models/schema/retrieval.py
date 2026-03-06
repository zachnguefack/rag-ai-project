from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["What is the reimbursement limit for meals?"])
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$", examples=["balanced"])
    strict_document_scope: bool | None = Field(
        default=None,
        description="When true, only returns answers if sufficient authorized document evidence is found.",
        examples=[True],
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional strict scope document IDs (internal IDs only, never filesystem paths).",
        examples=[["doc-ops"]],
    )


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence_score: float
