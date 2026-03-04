def emit_audit_event(action: str, actor: str, payload: dict) -> dict:
    return {"action": action, "actor": actor, "payload": payload}
