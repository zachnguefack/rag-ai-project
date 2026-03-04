class AuditService:
    def record(self, action: str, actor: str, payload: dict) -> dict:
        return {"action": action, "actor": actor, "payload": payload}
