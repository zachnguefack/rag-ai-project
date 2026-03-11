from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["What is the reimbursement limit for meals?"])
    department_id: str | None = Field(
        default=None,
        min_length=2,
        description=(
            "Optional department scope override. When omitted, the backend automatically searches "
            "across all departments assigned to the authenticated user."
        ),
        examples=["dept-it"],
    )
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$", examples=["balanced"])
    strict_document_scope: bool | None = Field(
        default=None,
        description="When true, only returns answers if sufficient authorized document evidence is found.",
        examples=[True],
    )
    document_ids: list[str] | None = Field(
        default=None,
        description=(
            "Optional internal document IDs to further narrow search scope. "
            "Any unauthorized ID triggers 403 and is never silently expanded."
        ),
        examples=[["doc-ops"]],
    )


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence_score: float
