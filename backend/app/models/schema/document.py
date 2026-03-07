from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    force_reindex: bool = Field(default=False, description="Forces complete re-indexing instead of incremental indexing.")


class IndexResponse(BaseModel):
    indexed_files: int
    indexed_chunks: int
    removed_files: int
    reused_existing_index: bool


class DocumentAccessResponse(BaseModel):
    document_id: str
    message: str


class DocumentMetadataResponse(BaseModel):
    department_id: str = Field(..., examples=["dept-finance"])
    owner: str = Field(..., examples=["jane.doe"])
    classification: str = Field(..., examples=["internal"])
    document_type: str = Field(default="policy", examples=["policy"])
    status: str = Field(default="active", examples=["active"])


class DocumentCreateRequest(BaseModel):
    document_id: str = Field(..., examples=["policy-2026-001"], description="Internal document identifier, never a filesystem path.")
    title: str = Field(..., examples=["Travel and Expense Policy"])
    content: str = Field(..., examples=["Employees must submit expense reports within 30 days..."])
    metadata: DocumentMetadataResponse


class DocumentUpdateRequest(BaseModel):
    title: str = Field(..., examples=["Travel and Expense Policy (Revised)"])
    content: str = Field(..., examples=["Updated policy content..."])
    metadata: DocumentMetadataResponse


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    current_version: int
    content: str
    metadata: DocumentMetadataResponse
    created_at: datetime
    updated_at: datetime


class DocumentVersionResponse(BaseModel):
    version: int
    content: str
    metadata: DocumentMetadataResponse


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool


class DocumentSummaryResponse(BaseModel):
    document_id: str = Field(..., examples=["doc-ops"], description="Internal document identifier.")
    title: str = Field(..., examples=["Operations Handbook"])
    department_id: str = Field(..., examples=["dept-operations"])
    owner: str = Field(..., examples=["u-standard"])
    classification: str = Field(..., examples=["internal"])
    document_type: str = Field(..., examples=["handbook"])
    status: str = Field(..., examples=["active"])
    updated_at: datetime
    current_version: int
    indexed: bool = Field(..., description="Indicates whether this document has at least one indexed version.")


class DocumentListResponse(BaseModel):
    items: list[DocumentSummaryResponse] = Field(default_factory=list)
    count: int
    total: int
    limit: int
    offset: int


class DocumentSearchResponse(DocumentListResponse):
    query: str = Field(..., examples=["operations"])


class DocumentMetadataDetailResponse(BaseModel):
    document_id: str = Field(..., examples=["doc-ops"], description="Internal document identifier.")
    title: str
    department_id: str
    owner: str
    classification: str
    document_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_version: int
    indexed: bool


class DocumentContentResponse(BaseModel):
    document_id: str = Field(..., examples=["doc-ops"], description="Internal document identifier.")
    content: str
    current_version: int


class DocumentACLGrantResponse(BaseModel):
    user_id: str = Field(..., examples=["u-analyst"])
    granted_at: datetime
    granted_by: str


class DocumentACLRevocationResponse(BaseModel):
    user_id: str = Field(..., examples=["u-analyst"])
    revoked_at: datetime


class DocumentACLResponse(BaseModel):
    document_id: str = Field(..., examples=["doc-ops"], description="Internal document identifier.")
    owning_department: str = Field(..., examples=["dept-operations"])
    owner: str = Field(..., examples=["u-standard"])
    classification: str = Field(..., examples=["internal"])
    status: str = Field(..., examples=["active"])
    explicit_user_grants: list[DocumentACLGrantResponse] = Field(default_factory=list)
    revoked_grants: list[DocumentACLRevocationResponse] = Field(default_factory=list)


class DocumentDepartmentAssignmentRequest(BaseModel):
    department_id: str = Field(..., examples=["dept-qa"])


class AdminDocumentListResponse(DocumentListResponse):
    pass


class DocumentAuditEventResponse(BaseModel):
    event_id: str = Field(..., examples=["evt-123"])
    action: str = Field(..., examples=["queried"])
    actor_user_id: str = Field(..., examples=["u-standard"])
    timestamp: datetime
    details: str = Field(..., examples=["Document was retrieved during a question-answer flow."])


class DocumentAuditListResponse(BaseModel):
    items: list[DocumentAuditEventResponse] = Field(default_factory=list)
    count: int


DocumentSummaryResponse.model_config = {
    "json_schema_extra": {
        "example": {
            "document_id": "doc-ops",
            "title": "Operations Handbook",
            "department_id": "dept-operations",
            "owner": "u-standard",
            "classification": "internal",
            "document_type": "handbook",
            "status": "active",
            "updated_at": "2026-01-20T10:12:00Z",
            "current_version": 3,
            "indexed": True,
        }
    }
}

DocumentDepartmentAssignmentRequest.model_config = {
    "json_schema_extra": {"example": {"department_id": "dept-qa"}}
}


DocumentListResponse.model_config = {
    "json_schema_extra": {
        "example": {
            "items": [DocumentSummaryResponse.model_config["json_schema_extra"]["example"]],
            "count": 1,
            "total": 12,
            "limit": 50,
            "offset": 0,
        }
    }
}

DocumentSearchResponse.model_config = {
    "json_schema_extra": {
        "example": {
            **DocumentListResponse.model_config["json_schema_extra"]["example"],
            "query": "operations",
        }
    }
}

DocumentMetadataDetailResponse.model_config = {
    "json_schema_extra": {
        "example": {
            "document_id": "doc-ops",
            "title": "Operations Handbook",
            "department_id": "dept-operations",
            "owner": "u-standard",
            "classification": "internal",
            "document_type": "handbook",
            "status": "active",
            "created_at": "2026-01-10T10:12:00Z",
            "updated_at": "2026-01-20T10:12:00Z",
            "current_version": 3,
            "indexed": True,
        }
    }
}

DocumentContentResponse.model_config = {
    "json_schema_extra": {
        "example": {"document_id": "doc-ops", "content": "Standard operations handbook", "current_version": 1}
    }
}

DocumentACLResponse.model_config = {
    "json_schema_extra": {
        "example": {
            "document_id": "doc-ops",
            "owning_department": "dept-operations",
            "owner": "u-standard",
            "classification": "internal",
            "status": "active",
            "explicit_user_grants": [
                {"user_id": "u-analyst", "granted_at": "2026-01-21T12:00:00Z", "granted_by": "u-admin"}
            ],
            "revoked_grants": [
                {"user_id": "u-former", "revoked_at": "2026-01-22T12:00:00Z"}
            ],
        }
    }
}

AdminDocumentListResponse.model_config = DocumentListResponse.model_config

DocumentAuditEventResponse.model_config = {
    "json_schema_extra": {
        "example": {
            "event_id": "evt-123",
            "action": "queried",
            "actor_user_id": "u-standard",
            "timestamp": "2026-01-20T09:00:00Z",
            "details": "Question: What is the latest operations SOP?",
        }
    }
}
