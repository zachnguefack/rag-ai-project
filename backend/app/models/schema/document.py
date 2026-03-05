from __future__ import annotations

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    force_reindex: bool = False


class IndexResponse(BaseModel):
    indexed_files: int
    indexed_chunks: int
    removed_files: int
    reused_existing_index: bool


class DocumentAccessResponse(BaseModel):
    document_id: str
    message: str


class DocumentMetadataResponse(BaseModel):
    department: str
    owner: str
    classification: str
    permissions: list[str] = Field(default_factory=list)


class DocumentCreateRequest(BaseModel):
    document_id: str
    title: str
    content: str
    metadata: DocumentMetadataResponse


class DocumentUpdateRequest(BaseModel):
    title: str
    content: str
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
