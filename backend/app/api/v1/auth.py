from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service, get_current_user, validate_api_key
from app.models.domain.user import User
from app.models.schema.auth import AuthTokenResponse, LoginRequest, LogoutResponse, MeResponse, RegisterRequest
from app.security.oauth2 import extract_bearer_token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post('/register', response_model=MeResponse, dependencies=[Depends(validate_api_key)])
def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)) -> MeResponse:
    record = auth_service.register_user(request.username, str(request.email), request.password)
    user = auth_service.hydrate_user(record)
    return MeResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        roles=sorted(user.role_names, key=lambda role: role.value),
    )


@router.post('/login', response_model=AuthTokenResponse, dependencies=[Depends(validate_api_key)])
def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthTokenResponse:
    user = auth_service.authenticate(request.username, request.password)
    token, expires_at = auth_service.issue_access_token(user)
    return AuthTokenResponse(access_token=token, expires_at=expires_at)


@router.post('/logout', response_model=LogoutResponse, dependencies=[Depends(validate_api_key)])
def logout(token: str = Depends(extract_bearer_token), auth_service: AuthService = Depends(get_auth_service)) -> LogoutResponse:
    auth_service.revoke_token(token)
    return LogoutResponse()


@router.get('/me', response_model=MeResponse, dependencies=[Depends(validate_api_key)])
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=sorted(current_user.role_names, key=lambda role: role.value),
    )
