from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from langchain_openai import ChatOpenAI

from .citations import extract_citations
from .postprocess import retrieve_postprocessed
from .prompting import SYSTEM_PROMPT_BALANCED, SYSTEM_PROMPT_STRICT, build_context, build_user_prompt

LOGGER = logging.getLogger("rag_v2.answer")


@dataclass(slots=True)
class AnswerPolicy:
    mode: str = "balanced"  # balanced|strict
    top_k_retrieve: int = 20
    final_k: int = 6
    score_threshold: float = 0.25
    lambda_mult: float = 0.75
    min_results: int = 2
    min_confidence: float = 0.40


class RAGService:
    def __init__(self, retriever, model: str = "gpt-4.1-mini"):
        self.retriever = retriever
        self.llm = ChatOpenAI(model=model, temperature=0.0)

    @staticmethod
    def compute_confidence(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        scores = [r.get("hybrid_score", r.get("similarity_score")) for r in results if isinstance(r.get("hybrid_score", r.get("similarity_score")), (float, int))]
        if not scores:
            return {"score": 0.0, "label": "none", "details": {"reason": "no_scores"}}

        arr = np.clip(np.array(scores, dtype=float), 0.0, 1.0)
        top1 = float(arr[0])
        top3 = float(np.mean(arr[: min(3, len(arr))]))
        conf = float(np.clip(0.65 * top1 + 0.35 * top3, 0.0, 1.0))
        label = "high" if conf >= 0.65 else "medium" if conf >= 0.45 else "low"
        return {"score": round(conf, 4), "label": label, "details": {"top1": round(top1, 4), "top3_mean": round(top3, 4), "n": len(arr)}}

    def answer(
        self,
        question: str,
        policy: AnswerPolicy | None = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        policy = policy or AnswerPolicy()

        results = retrieve_postprocessed(
            self.retriever,
            question,
            top_k_retrieve=policy.top_k_retrieve,
            final_k=policy.final_k,
            score_threshold=policy.score_threshold,
            metadata_filter=metadata_filter,
            lambda_mult=policy.lambda_mult,
        )
        confidence = self.compute_confidence(results)
        doc_grounded = len(results) >= policy.min_results and confidence["score"] >= policy.min_confidence

        if not doc_grounded and policy.mode == "strict":
            return {
                "answer": "Insufficient evidence in provided documents.",
                "mode": "strict",
                "source_type": "documents",
                "doc_grounded": False,
                "confidence": confidence,
                "citations": [],
            }

        context = build_context(results)
        prompt = build_user_prompt(question, context)
        system_prompt = SYSTEM_PROMPT_STRICT if policy.mode == "strict" else SYSTEM_PROMPT_BALANCED

        response = self.llm.invoke([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}])
        answer_text = response.content

        if not doc_grounded and policy.mode != "strict":
            LOGGER.info("Fallback to general answer for question due to weak retrieval")
            return {
                "answer": "⚠️ Source: general knowledge (documents not sufficiently relevant).\n\n" + answer_text,
                "mode": "balanced",
                "source_type": "general_knowledge",
                "doc_grounded": False,
                "confidence": confidence,
                "citations": [],
            }

        return {
            "answer": answer_text,
            "mode": policy.mode,
            "source_type": "documents",
            "doc_grounded": True,
            "confidence": confidence,
            "citations": extract_citations(results),
        }


def rag_answer(question, rag_retriever, mode="personal", model="gpt-4.1-mini", top_k_retrieve=20, final_k=6, score_threshold=0.25, lambda_mult=0.75, metadata_filter=None, fallback_conf_threshold=0.40):
    policy_mode = "strict" if mode in {"enterprise", "strict"} else "balanced"
    policy = AnswerPolicy(
        mode=policy_mode,
        top_k_retrieve=top_k_retrieve,
        final_k=final_k,
        score_threshold=score_threshold,
        lambda_mult=lambda_mult,
        min_confidence=fallback_conf_threshold,
    )
    service = RAGService(retriever=rag_retriever, model=model)
    out = service.answer(question, policy=policy, metadata_filter=metadata_filter)
    out["mode"] = mode
    return out
