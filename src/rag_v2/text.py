from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 42
SUPPORTED_LANGS = {"fr", "en", "it"}


def detect_language_safe(text: str) -> str:
    if not text:
        return "unknown"
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) < 40:
        return "unknown"
    try:
        lang = detect(compact)
        return lang if lang in SUPPORTED_LANGS else "other"
    except Exception:
        return "unknown"


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def prepare_chunks(chunks: List[Any]) -> Tuple[List[Any], List[str]]:
    filtered: List[Any] = []
    texts: List[str] = []

    for doc in chunks:
        raw = getattr(doc, "page_content", "") or ""
        cleaned = clean_text(raw)
        if not cleaned:
            continue

        doc.page_content = cleaned
        md: Dict[str, Any] = getattr(doc, "metadata", {}) or {}

        if "source" in md:
            md["source"] = str(md["source"])

        if "page" in md:
            try:
                md["page"] = int(md["page"])
            except Exception:
                md["page"] = 0

        md["lang"] = detect_language_safe(cleaned)

        doc.metadata = md
        filtered.append(doc)
        texts.append(cleaned)

    return filtered, texts


def assign_chunk_index_per_page(chunks: List[Any]) -> List[Any]:
    counters: Dict[Tuple[str, int], int] = {}
    for doc in chunks:
        md = getattr(doc, "metadata", {}) or {}
        src = str(md.get("source") or md.get("file_path") or "unknown_source")
        page = int(md.get("page") or 0)
        key = (src, page)
        counters[key] = counters.get(key, 0) + 1
        md["chunk_index"] = counters[key] - 1
        md["chunk_len"] = len(getattr(doc, "page_content", "") or "")
        doc.metadata = md
    return chunks