from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserDocumentAccessRecord(BaseModel):
    id: str = Field(..., examples=["uda-1"])
    user_id: str = Field(..., examples=["u-123"])
    document_id: str = Field(..., examples=["doc-finance-policy"])
    granted_by: str = Field(..., examples=["u-admin"])
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: datetime | None = None
    is_active: bool = True
