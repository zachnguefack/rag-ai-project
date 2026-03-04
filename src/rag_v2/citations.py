from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple


def _citation_key(metadata: Dict[str, Any]) -> Tuple[str, Any, Any]:
    label = metadata.get("doc_title") or metadata.get("doc_id") or os.path.basename(str(metadata.get("source", ""))) or "Document"
    return label, metadata.get("page"), metadata.get("chunk_index")


def extract_citations(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    seen = set()
    c_idx = 1

    for row in results:
        md = row.get("metadata", {}) or {}
        key = _citation_key(md)
        if key in seen:
            continue
        seen.add(key)

        label, page, chunk_index = key
        page_display = page + 1 if isinstance(page, int) else page
        refs.append(
            {
                "ref": f"C{c_idx}",
                "document": label,
                "page": page_display if page_display is not None else "—",
                "chunk_index": chunk_index if chunk_index is not None else "—",
            }
        )
        c_idx += 1

    return refs


def format_sources(citations: List[Dict[str, Any]]) -> str:
    lines = []
    for c in citations:
        page = c.get("page")
        chunk = c.get("chunk_index")
        page_str = "no page" if page in (None, "—", "?") else f"p.{page}"
        lines.append(f"- [{c['ref']}] {c['document']} ({page_str}, chunk={chunk})")
    return "\n".join(lines)


# Backward-compatible aliases
extract_citations_generic = extract_citations
format_sources_generic = format_sources
