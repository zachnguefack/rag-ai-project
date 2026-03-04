from __future__ import annotations

from typing import Any, Dict, List


def build_context_with_citations(results: List[Dict[str, Any]], max_chars_per_chunk: int = 1200) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        md = r.get("metadata", {}) or {}
        source = str(md.get("source", "Document"))
        page = md.get("page", None)
        page_disp = page + 1 if isinstance(page, int) else page

        text = (r.get("content") or "").strip()
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk] + "..."

        citation = f"[C{i} | {source} | p.{page_disp}]"
        blocks.append(f"{citation}\n{text}")

    return "\n\n---\n\n".join(blocks)


SYSTEM_PROMPT_STRICT = """You are an internal documentation assistant.
Rules:
- Use ONLY the provided CONTEXT.
- If the CONTEXT does not contain enough information, answer exactly:
  "Insufficient evidence in provided documents."
- Do NOT invent procedures, steps, numbers, or compliance statements.
- Every key statement must include at least one citation tag like [C1] or [C2].
"""


SYSTEM_PROMPT_PERSONAL = """You are a helpful assistant.

You may use:
1) Provided CONTEXT (documents)
2) Your general knowledge (ChatGPT)

Rules:
- If context is strong and relevant, use it and cite with [C#].
- If context is weak or insufficient, answer using general knowledge.
- NEVER invent citations.
- If using general knowledge, do not add citation tags.
- Keep answer clear and structured.
"""


def build_user_prompt(question: str, context: str) -> str:
    return f"""CONTEXT:
{context}

QUESTION:
{question}

OUTPUT FORMAT:
- Provide a clear answer.
- Use bullet points for procedures/steps.
- Add citations like [C1] after the statements they support.
- If insufficient: "Insufficient evidence in provided documents."
"""