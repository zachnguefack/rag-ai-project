from __future__ import annotations

import re


def normalize_document_id(value: str) -> str:
    """Normalize source identifiers into a stable document_id token."""
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip()).strip("-._").lower()
    return normalized

