from __future__ import annotations


def fuse_results(vector_hits: list[dict], keyword_hits: list[dict]) -> list[dict]:
    return vector_hits or keyword_hits
