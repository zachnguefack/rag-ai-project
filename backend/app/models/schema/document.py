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
    department: str = Field(..., examples=["Finance"])
    owner: str = Field(..., examples=["jane.doe"])
    classification: str = Field(..., examples=["internal"])
    status: str = Field(default="approved", examples=["approved"])
    permissions: list[str] = Field(default_factory=list, examples=[["read", "update"]])
    allowed_departments: list[str] = Field(default_factory=list, examples=[["finance", "operations"]])


class DocumentCreateRequest(BaseModel):
    document_id: str = Field(..., description="Internal document identifier. Not a file path.", examples=["policy-2026-001"])
    title: str = Field(..., examples=["Travel and Expense Policy"])
    document_type: str = Field(default="sop", examples=["sop"])
    content: str = Field(..., examples=["Employees must submit expense reports within 30 days..."])
    metadata: DocumentMetadataResponse


class DocumentUpdateRequest(BaseModel):
    title: str = Field(..., examples=["Travel and Expense Policy (Revised)"])
    document_type: str = Field(default="sop", examples=["policy"])
    content: str = Field(..., examples=["Updated policy content..."])
    metadata: DocumentMetadataResponse


class DocumentResponse(BaseModel):
    document_id: str
    title: str
    document_type: str
    status: str
    current_version: int
    content: str
    created_at: datetime
    updated_at: datetime
    metadata: DocumentMetadataResponse


class DocumentVersionResponse(BaseModel):
    version_id: str
    document_id: str
    version_number: int
    storage_path: str
    checksum: str
    indexed: bool
    approved_at: datetime | None
    content: str
    metadata: DocumentMetadataResponse


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
