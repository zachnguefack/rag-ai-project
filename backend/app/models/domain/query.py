from dataclasses import dataclass


@dataclass
class Query:
    text: str
    top_k: int = 5
