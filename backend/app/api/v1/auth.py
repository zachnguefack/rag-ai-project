from fastapi import APIRouter, Depends

from app.models.schema.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, service: AuthService = Depends(AuthService)) -> TokenResponse:
    return service.login(payload.username, payload.password)
