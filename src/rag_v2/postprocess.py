from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


def dedup_results_by_source_page(
    results: List[Dict[str, Any]],
    max_per_source: int = 3,
    max_per_page: int = 1,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    per_source = {}
    per_page = {}

    for r in results:
        md = r.get("metadata", {}) or {}
        source = str(md.get("source", "unknown_source"))
        page = int(md.get("page", 0) or 0)
        page_key = (source, page)

        per_source[source] = per_source.get(source, 0)
        per_page[page_key] = per_page.get(page_key, 0)

        if per_source[source] >= max_per_source:
            continue
        if per_page[page_key] >= max_per_page:
            continue

        out.append(r)
        per_source[source] += 1
        per_page[page_key] += 1

    return out


def _tokenize(text: str) -> Set[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9àâäçéèêëîïôöùûüœæ'\s-]", " ", text)
    return set(t for t in text.split() if len(t) >= 3)


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def mmr_lite(
    results: List[Dict[str, Any]],
    k: int = 5,
    lambda_mult: float = 0.75,
) -> List[Dict[str, Any]]:
    if not results:
        return []

    candidates = sorted(results, key=lambda x: x.get("similarity_score", 0), reverse=True)
    selected: List[Dict[str, Any]] = []
    selected_tokens: List[Set[str]] = []
    cand_tokens = [_tokenize(r.get("content", "")) for r in candidates]

    while candidates and len(selected) < k:
        best_idx = 0
        best_score = -1e9

        for i, r in enumerate(candidates):
            rel = float(r.get("similarity_score", 0.0))
            if not selected:
                mmr_score = rel
            else:
                redund = max(_jaccard(cand_tokens[i], t) for t in selected_tokens) if selected_tokens else 0.0
                div = 1.0 - redund
                mmr_score = lambda_mult * rel + (1.0 - lambda_mult) * div

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        chosen = candidates.pop(best_idx)
        chosen_tok = cand_tokens.pop(best_idx)

        selected.append(chosen)
        selected_tokens.append(chosen_tok)

    return selected


def retrieve_postprocessed(
    rag_retriever,
    query: str,
    top_k_retrieve: int = 12,
    final_k: int = 5,
    score_threshold: float = 0.2,
    metadata_filter: Optional[Dict[str, Any]] = None,
    max_per_source: int = 3,
    max_per_page: int = 1,
    lambda_mult: float = 0.75,
) -> List[Dict[str, Any]]:

    raw = rag_retriever.retrieve(
        query,
        top_k=top_k_retrieve,
        score_threshold=score_threshold,
        metadata_filter=metadata_filter,
    )

    deduped = dedup_results_by_source_page(raw, max_per_source=max_per_source, max_per_page=max_per_page)
    diversified = mmr_lite(deduped, k=final_k, lambda_mult=lambda_mult)
    return diversified