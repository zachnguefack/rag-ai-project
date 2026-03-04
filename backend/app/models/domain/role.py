from dataclasses import dataclass


@dataclass
class Role:
    name: str
    permissions: list[str]
