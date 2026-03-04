from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    return {"status": "ready"}
