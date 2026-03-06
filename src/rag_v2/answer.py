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

NO_RELEVANT_DOCUMENTS_MESSAGE = (
    "No relevant information was found in the available documentation.  \n"
    "Your question may be outside the scope of the company's knowledge base.  \n"
    "Please contact your administrator or the relevant department for further assistance."
)


@dataclass(slots=True)
class AnswerPolicy:
    """Configuration for retrieval + generation behavior in the answer pipeline."""

    mode: str = "balanced"  # balanced|strict
    top_k_retrieve: int = 20
    final_k: int = 6
    score_threshold: float = 0.25
    lambda_mult: float = 0.75
    min_results: int = 2
    min_confidence: float = 0.40
    strict_document_scope: bool = False
    no_relevant_docs_message: str = NO_RELEVANT_DOCUMENTS_MESSAGE


class RAGService:
    """Retrieve document evidence and generate an answer using the configured policy."""

    def __init__(self, retriever, model: str = "gpt-4.1-mini"):
        self.retriever = retriever
        self.llm = ChatOpenAI(model=model, temperature=0.0)

    @staticmethod
    def compute_confidence(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute a confidence score from retrieval scores."""
        scores = [
            r.get("hybrid_score", r.get("similarity_score"))
            for r in results
            if isinstance(r.get("hybrid_score", r.get("similarity_score")), (float, int))
        ]
        if not scores:
            return {"score": 0.0, "label": "none", "details": {"reason": "no_scores"}}

        arr = np.clip(np.array(scores, dtype=float), 0.0, 1.0)
        top1 = float(arr[0])
        top3 = float(np.mean(arr[: min(3, len(arr))]))
        conf = float(np.clip(0.65 * top1 + 0.35 * top3, 0.0, 1.0))
        label = "high" if conf >= 0.65 else "medium" if conf >= 0.45 else "low"
        return {
            "score": round(conf, 4),
            "label": label,
            "details": {"top1": round(top1, 4), "top3_mean": round(top3, 4), "n": len(arr)},
        }

    @staticmethod
    def _document_scope_required(policy: AnswerPolicy) -> bool:
        """Return True when generation must stay document-only."""
        return policy.strict_document_scope or policy.mode == "strict"

    @staticmethod
    def _has_sufficient_retrieval_evidence(
        results: List[Dict[str, Any]],
        confidence: Dict[str, Any],
        policy: AnswerPolicy,
    ) -> bool:
        """Validate retrieved evidence before generation."""
        enough_results = len(results) >= policy.min_results
        enough_confidence = confidence["score"] >= policy.min_confidence
        return enough_results and enough_confidence

    @staticmethod
    def _strict_scope_rejection(policy: AnswerPolicy, confidence: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deterministic enterprise-safe response for out-of-scope queries."""
        return {
            "answer": policy.no_relevant_docs_message,
            "mode": policy.mode,
            "source_type": "documents",
            "doc_grounded": False,
            "confidence": confidence,
            "citations": [],
        }

    def answer(
        self,
        question: str,
        policy: Optional[AnswerPolicy] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        user: Any | None = None,
    ) -> Dict[str, Any]:
        """Run retrieval, validate evidence, and optionally call the LLM."""
        policy = policy or AnswerPolicy()

        results = retrieve_postprocessed(
            self.retriever,
            question,
            top_k_retrieve=policy.top_k_retrieve,
            final_k=policy.final_k,
            score_threshold=policy.score_threshold,
            metadata_filter=metadata_filter,
            lambda_mult=policy.lambda_mult,
            user=user,
        )
        confidence = self.compute_confidence(results)
        doc_grounded = self._has_sufficient_retrieval_evidence(results, confidence, policy)

        strict_document_scope_enabled = self._document_scope_required(policy)
        if strict_document_scope_enabled and not doc_grounded:
            return self._strict_scope_rejection(policy, confidence)

        context = build_context(results)
        prompt = build_user_prompt(question, context)
        system_prompt = SYSTEM_PROMPT_STRICT if strict_document_scope_enabled else SYSTEM_PROMPT_BALANCED

        response = self.llm.invoke(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        )
        answer_text = response.content

        if not doc_grounded:
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


def rag_answer(
    question: str,
    rag_retriever: Any,
    mode: str = "personal",
    model: str = "gpt-4.1-mini",
    top_k_retrieve: int = 20,
    final_k: int = 6,
    score_threshold: float = 0.25,
    lambda_mult: float = 0.75,
    metadata_filter: Optional[Dict[str, Any]] = None,
    fallback_conf_threshold: float = 0.40,
    strict_document_scope: bool = False,
) -> Dict[str, Any]:
    """Backward-compatible helper for one-shot question answering."""
    policy_mode = "strict" if mode in {"enterprise", "strict"} else "balanced"
    policy = AnswerPolicy(
        mode=policy_mode,
        top_k_retrieve=top_k_retrieve,
        final_k=final_k,
        score_threshold=score_threshold,
        lambda_mult=lambda_mult,
        min_confidence=fallback_conf_threshold,
        strict_document_scope=strict_document_scope,
    )
    service = RAGService(retriever=rag_retriever, model=model)
    out = service.answer(question, policy=policy, metadata_filter=metadata_filter)
    out["mode"] = mode
    return out
