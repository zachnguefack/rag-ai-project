from fastapi import APIRouter, Depends

from app.api.deps import permission_dependency

router = APIRouter()


@router.get("/stats")
def stats(_: dict = Depends(permission_dependency("admin:read"))) -> dict:
    return {"service": "rag-backend", "mode": "production-ready"}
