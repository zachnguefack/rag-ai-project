from dataclasses import dataclass


@dataclass
class Document:
    id: int
    title: str
    content: str
