from __future__ import annotations


def document_id_filter(document_ids: list[str]) -> dict[str, dict[str, list[str]]]:
    return {"document_id": {"$in": document_ids}}
