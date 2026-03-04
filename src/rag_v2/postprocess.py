from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set


_TOKEN_RE = re.compile(r"[^a-z0-9àâäçéèêëîïôöùûüœæ'\s-]+")


def _tokenize(text: str) -> Set[str]:
    text = _TOKEN_RE.sub(" ", (text or "").lower())
    return {t for t in text.split() if len(t) >= 3}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _keyword_coverage(query_tokens: Set[str], content_tokens: Set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(query_tokens & content_tokens) / len(query_tokens)


def dedup_results_by_source_page(results: List[Dict[str, Any]], max_per_source: int = 3, max_per_page: int = 1) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    source_counts: Dict[str, int] = {}
    page_counts: Dict[tuple[str, int], int] = {}

    for row in results:
        md = row.get("metadata", {}) or {}
        source = str(md.get("source", "unknown_source"))
        page = int(md.get("page", 0) or 0)
        key = (source, page)

        if source_counts.get(source, 0) >= max_per_source:
            continue
        if page_counts.get(key, 0) >= max_per_page:
            continue

        selected.append(row)
        source_counts[source] = source_counts.get(source, 0) + 1
        page_counts[key] = page_counts.get(key, 0) + 1

    return selected


def rank_with_hybrid_score(results: List[Dict[str, Any]], query: str, alpha_semantic: float = 0.8) -> List[Dict[str, Any]]:
    query_toks = _tokenize(query)
    ranked = []
    for row in results:
        sem = float(row.get("similarity_score", 0.0))
        lex = _keyword_coverage(query_toks, _tokenize(row.get("content", "")))
        hybrid = alpha_semantic * sem + (1 - alpha_semantic) * lex
        item = dict(row)
        item["lexical_score"] = round(lex, 6)
        item["hybrid_score"] = round(hybrid, 6)
        ranked.append(item)
    ranked.sort(key=lambda r: r["hybrid_score"], reverse=True)
    return ranked


def mmr_select(results: List[Dict[str, Any]], k: int = 6, lambda_mult: float = 0.75) -> List[Dict[str, Any]]:
    if not results:
        return []

    candidates = sorted(results, key=lambda x: x.get("hybrid_score", x.get("similarity_score", 0.0)), reverse=True)
    tokens = [_tokenize(c.get("content", "")) for c in candidates]
    chosen: List[Dict[str, Any]] = []
    chosen_toks: List[Set[str]] = []

    while candidates and len(chosen) < k:
        best_idx = 0
        best_score = -math.inf
        for i, row in enumerate(candidates):
            rel = float(row.get("hybrid_score", row.get("similarity_score", 0.0)))
            if not chosen_toks:
                score = rel
            else:
                redundancy = max(_jaccard(tokens[i], ct) for ct in chosen_toks)
                score = lambda_mult * rel + (1.0 - lambda_mult) * (1.0 - redundancy)
            if score > best_score:
                best_score = score
                best_idx = i

        chosen.append(candidates.pop(best_idx))
        chosen_toks.append(tokens.pop(best_idx))

    return chosen


def retrieve_postprocessed(
    rag_retriever,
    query: str,
    top_k_retrieve: int = 20,
    final_k: int = 6,
    score_threshold: float = 0.25,
    metadata_filter: Optional[Dict[str, Any]] = None,
    max_per_source: int = 3,
    max_per_page: int = 1,
    lambda_mult: float = 0.75,
) -> List[Dict[str, Any]]:
    raw = rag_retriever.retrieve(query, top_k=top_k_retrieve, score_threshold=score_threshold, metadata_filter=metadata_filter)
    deduped = dedup_results_by_source_page(raw, max_per_source=max_per_source, max_per_page=max_per_page)
    ranked = rank_with_hybrid_score(deduped, query)
    return mmr_select(ranked, k=final_k, lambda_mult=lambda_mult)
