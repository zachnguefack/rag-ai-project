from __future__ import annotations

from pydantic import BaseModel


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
