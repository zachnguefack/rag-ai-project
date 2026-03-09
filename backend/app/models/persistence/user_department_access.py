from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserDepartmentAccessRecord(BaseModel):
    id: str = Field(..., examples=["uda-dept-1"])
    user_id: str = Field(..., examples=["u-123"])
    department_id: str = Field(..., examples=["dept-it"])
    assigned_by: str = Field(..., examples=["u-admin"])
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

