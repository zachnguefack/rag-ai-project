from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class DepartmentRecord(BaseModel):
    id: int | None = None
    department_id: str = Field(..., examples=["dept-finance"])
    name: str = Field(..., examples=["Finance"])
    slug: str = Field(..., examples=["finance"])
    description: str = Field(default="", examples=["Financial planning and accounting."])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
