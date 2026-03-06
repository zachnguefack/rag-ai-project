from __future__ import annotations

from pydantic import BaseModel, Field


class DepartmentRecord(BaseModel):
    department_id: str = Field(..., examples=["dept-finance"])
    name: str = Field(..., examples=["Finance"])
    description: str = Field(default="", examples=["Financial planning and accounting."])
