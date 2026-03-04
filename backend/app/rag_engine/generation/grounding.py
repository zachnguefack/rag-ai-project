def has_sufficient_evidence(results: list[dict], min_results: int = 1) -> bool:
    return len(results) >= min_results
