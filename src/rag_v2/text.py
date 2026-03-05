from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langdetect import DetectorFactory, detect
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    DetectorFactory = None
    detect = None

if DetectorFactory is not None:
    DetectorFactory.seed = 42
SUPPORTED_LANGS = {"fr", "en", "it"}


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def detect_language_safe(text: str) -> str:
    if detect is None:
        return "unknown"

    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) < 40:
        return "unknown"
    try:
        lang = detect(compact)
    except Exception:
        return "unknown"
    return lang if lang in SUPPORTED_LANGS else "other"


def split_documents(
    documents: Iterable[Document],
    chunk_size: int = 900,
    chunk_overlap: int = 140,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    prepared_docs: List[Document] = []
    for doc in documents:
        content = clean_text(getattr(doc, "page_content", "") or "")
        if not content:
            continue
        metadata: Dict[str, Any] = dict(getattr(doc, "metadata", {}) or {})
        metadata["lang"] = detect_language_safe(content)
        prepared_docs.append(Document(page_content=content, metadata=metadata))

    chunks = splitter.split_documents(prepared_docs)
    return assign_chunk_indices(chunks)


def assign_chunk_indices(chunks: List[Document]) -> List[Document]:
    counters: Dict[Tuple[str, int], int] = {}
    for chunk in chunks:
        md = dict(getattr(chunk, "metadata", {}) or {})
        source = str(md.get("source") or "unknown_source")
        page = int(md.get("page") or 0)
        key = (source, page)
        idx = counters.get(key, 0)
        counters[key] = idx + 1

        md["source"] = source
        md["page"] = page
        md["chunk_index"] = idx
        md["chunk_len"] = len(chunk.page_content)
        chunk.metadata = md

    return chunks
