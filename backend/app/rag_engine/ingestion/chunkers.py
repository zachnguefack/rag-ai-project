from __future__ import annotations


def chunking_config(chunk_size: int, chunk_overlap: int) -> dict[str, int]:
    return {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
