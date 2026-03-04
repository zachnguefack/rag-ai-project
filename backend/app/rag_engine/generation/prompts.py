def build_prompt(question: str, contexts: list[dict]) -> str:
    return f"Question: {question}\nContext: {[c['content'] for c in contexts]}"
