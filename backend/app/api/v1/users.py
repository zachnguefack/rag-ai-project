from fastapi import APIRouter, Depends

from app.api.deps import permission_dependency

router = APIRouter()


@router.get("/me")
def me(user: dict = Depends(permission_dependency("user:read"))) -> dict:
    return {"user": user}
