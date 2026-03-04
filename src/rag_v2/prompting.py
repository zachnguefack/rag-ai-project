from __future__ import annotations

from typing import Any, Dict, List


SYSTEM_PROMPT_STRICT = """You are an enterprise documentation assistant.
Rules:
- Use only the supplied CONTEXT.
- If context is insufficient, reply exactly: \"Insufficient evidence in provided documents.\"
- Every factual claim must include one citation tag like [C1].
- Never fabricate citations.
"""


SYSTEM_PROMPT_BALANCED = """You are a helpful assistant.
Use provided CONTEXT first. If insufficient, you can use general knowledge.
Rules:
- Cite document-grounded claims with [C#].
- If using general knowledge, do not add fake citations.
"""


def build_context(results: List[Dict[str, Any]], max_chars_per_chunk: int = 1400) -> str:
    blocks = []
    for i, row in enumerate(results, start=1):
        md = row.get("metadata", {}) or {}
        source = md.get("source", "Document")
        page = md.get("page")
        page_disp = page + 1 if isinstance(page, int) else page
        content = (row.get("content") or "").strip()
        if len(content) > max_chars_per_chunk:
            content = content[:max_chars_per_chunk] + "..."
        blocks.append(f"[C{i} | {source} | p.{page_disp}]\n{content}")
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(question: str, context: str) -> str:
    return (
        "CONTEXT:\n"
        f"{context}\n\n"
        "QUESTION:\n"
        f"{question}\n\n"
        "OUTPUT:\n"
        "- Provide a concise and factual answer.\n"
        "- Use bullet points for steps/procedures.\n"
        "- Add citation tags such as [C1].\n"
    )


# Backward-compatible aliases
SYSTEM_PROMPT_PERSONAL = SYSTEM_PROMPT_BALANCED
def build_context_with_citations(results, max_chars_per_chunk=1400):
    return build_context(results, max_chars_per_chunk=max_chars_per_chunk)
