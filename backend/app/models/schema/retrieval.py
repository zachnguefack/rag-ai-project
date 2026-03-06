from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["What is the reimbursement limit for meals?"])
    mode: str = Field(default="balanced", pattern="^(strict|balanced)$", examples=["balanced"])
    strict_document_scope: bool | None = Field(
        default=None,
        description="When true, only returns answers if sufficient document evidence is found.",
        examples=[True],
    )


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence_score: float
    authorized_document_ids_count: int = Field(default=0, description="Number of documents in computed secure retrieval scope.")
    strict_scope_blocked: bool = Field(default=False, description="True when strict scope blocked LLM generation.")
