from dataclasses import dataclass


@dataclass
class AuditEvent:
    action: str
    actor: str
    payload: dict
