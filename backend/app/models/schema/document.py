from __future__ import annotations

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
    permissions: list[str] = Field(default_factory=list, examples=[["read", "update"]])


class DocumentCreateRequest(BaseModel):
    document_id: str = Field(..., examples=["policy-2026-001"])
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


class DocumentVersionResponse(BaseModel):
    version: int
    content: str
    metadata: DocumentMetadataResponse


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted: bool
