def now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()
