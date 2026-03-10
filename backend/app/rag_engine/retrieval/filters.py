from __future__ import annotations


def document_id_filter(document_ids: list[str]) -> dict[str, dict[str, list[str]]]:
    return {"document_id": {"$in": document_ids}}


def department_id_filter(department_ids: list[str]) -> dict[str, dict[str, list[str]]]:
    return {"department_id": {"$in": department_ids}}


def combine_metadata_filters(*filters: dict | None) -> dict | None:
    valid = [f for f in filters if f]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0]
    return {"$and": valid}
