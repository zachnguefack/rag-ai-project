from app.models.schema.auth import TokenResponse
from app.security.jwt import create_access_token


class AuthService:
    def login(self, username: str, password: str) -> TokenResponse:
        if not username or not password:
            raise ValueError("Username/password required")
        role = "admin" if username == "admin" else "reader"
        token = create_access_token({"sub": username, "roles": [role]})
        return TokenResponse(access_token=token, token_type="bearer")
