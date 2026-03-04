from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
from langchain_openai import ChatOpenAI

from .postprocess import retrieve_postprocessed
from .prompting import (
    SYSTEM_PROMPT_PERSONAL,
    SYSTEM_PROMPT_STRICT,
    build_context_with_citations,
    build_user_prompt,
)
from .citations import extract_citations_generic


def compute_confidence(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    scores = [r.get("similarity_score") for r in results if isinstance(r.get("similarity_score"), (int, float))]
    if not scores:
        return {"score": 0.0, "label": "none", "details": {"reason": "no_scores"}}

    scores = np.array(scores, dtype=float)
    scores = np.clip(scores, 0.0, 1.0)

    top1 = float(scores[0])
    top3_mean = float(np.mean(scores[: min(3, len(scores))]))
    n = len(scores)

    conf = 0.65 * top1 + 0.35 * top3_mean
    if n == 1:
        conf *= 0.88
    elif n == 2:
        conf *= 0.95

    conf = float(np.clip(conf, 0.0, 1.0))
    label = "high" if conf >= 0.60 else "medium" if conf >= 0.40 else "low"

    return {"score": round(conf, 4), "label": label, "details": {"top1": round(top1, 4), "top3_mean": round(top3_mean, 4), "n_results_used": n}}


def _make_llm(model: str = "gpt-4.1-mini") -> ChatOpenAI:
    return ChatOpenAI(model=model, temperature=0.0)


def rag_answer(
    question: str,
    rag_retriever,
    mode: str = "personal",
    model: str = "gpt-4.1-mini",
    top_k_retrieve: int = 15,
    final_k: int = 6,
    score_threshold: float = 0.20,
    lambda_mult: float = 0.75,
    metadata_filter: Optional[Dict[str, Any]] = None,
    fallback_conf_threshold: float = 0.35,
) -> Dict[str, Any]:

    llm = _make_llm(model=model)

    results = retrieve_postprocessed(
        rag_retriever,
        question,
        top_k_retrieve=top_k_retrieve,
        final_k=final_k,
        score_threshold=score_threshold,
        lambda_mult=lambda_mult,
        metadata_filter=metadata_filter,
    )

    confidence = compute_confidence(results)
    doc_grounded = (len(results) >= 2) and (confidence["score"] >= fallback_conf_threshold)
    context = build_context_with_citations(results)

    if mode == "personal":
        user_prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\n"
        resp = llm.invoke([{"role": "system", "content": SYSTEM_PROMPT_PERSONAL}, {"role": "user", "content": user_prompt}])
        answer = resp.content

        if doc_grounded:
            return {
                "answer": answer,
                "mode": "personal",
                "source_type": "documents",
                "doc_grounded": True,
                "confidence": confidence,
                "citations": extract_citations_generic(results),
            }

        return {
            "answer": "⚠️ Source: ChatGPT (general knowledge — not found in your documents).\n\n" + answer,
            "mode": "personal",
            "source_type": "chatgpt",
            "doc_grounded": False,
            "confidence": confidence,
            "citations": [],
        }

    # enterprise strict
    if not doc_grounded:
        return {
            "answer": "Insufficient evidence in provided documents.",
            "mode": "enterprise",
            "source_type": "documents",
            "doc_grounded": False,
            "confidence": confidence,
            "citations": [],
        }

    resp = llm.invoke(
        [{"role": "system", "content": SYSTEM_PROMPT_STRICT}, {"role": "user", "content": build_user_prompt(question, context)}]
    )
    return {
        "answer": resp.content,
        "mode": "enterprise",
        "source_type": "documents",
        "doc_grounded": True,
        "confidence": confidence,
        "citations": extract_citations_generic(results),
    }