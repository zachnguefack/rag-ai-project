from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Invalid API key."])
