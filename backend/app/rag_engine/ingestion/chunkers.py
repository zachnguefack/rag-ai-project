def chunk_text(content: str, size: int = 500) -> list[str]:
    return [content[i : i + size] for i in range(0, len(content), size)] or [""]
