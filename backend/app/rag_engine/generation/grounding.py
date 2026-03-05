from __future__ import annotations


def is_grounded(confidence_score: float, threshold: float) -> bool:
    return confidence_score >= threshold
