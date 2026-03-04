from __future__ import annotations

import os
from typing import Any, Dict, List


def extract_citations_generic(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    citations = []
    seen = set()

    for i, r in enumerate(results, start=1):
        md = r.get("metadata", {}) or {}
        label = (
            md.get("doc_title")
            or md.get("doc_id")
            or os.path.basename(str(md.get("source", "")))
            or "Document"
        )

        page = md.get("page")
        page_display = page + 1 if isinstance(page, int) else page

        key = (label, page_display)
        if key in seen:
            continue
        seen.add(key)

        citations.append({"ref": f"C{i}", "document": label, "page": page_display if page_display is not None else "—"})

    return citations


def format_sources_generic(citations: List[Dict[str, Any]]) -> str:
    lines = []
    for c in citations:
        page = c.get("page")
        page_text = "no page" if page in (None, "—", "?") else f"p.{page}"
        lines.append(f"- [{c['ref']}] {c['document']} ({page_text})")
    return "\n".join(lines)