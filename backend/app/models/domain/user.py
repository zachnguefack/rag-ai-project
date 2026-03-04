from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    roles: list[str]
