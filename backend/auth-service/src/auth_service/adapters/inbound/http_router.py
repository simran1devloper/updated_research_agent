"""Inbound HTTP adapter — auth + user management REST endpoints."""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from ...application.use_cases import (
    RegisterUseCase, LoginUseCase, RefreshUseCase, LogoutUseCase,
    OAuthLoginUseCase, GetUserUseCase, ListUsersUseCase,
    UpdateUserUseCase, DeleteUserUseCase,
)
from ...domain.models import OAuthProvider, UserRole
from ...container import AuthContainer

router = APIRouter(tags=["auth"])

# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool


class UpdateUserRequest(BaseModel):
    username: str | None = None
    is_active: bool | None = None
    role: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _c() -> AuthContainer:
    return AuthContainer.instance()


def _user_out(user) -> UserOut:
    return UserOut(id=user.id, email=user.email, username=user.username,
                   role=user.role.value, is_active=user.is_active)


# ── Auth endpoints ────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest):
    try:
        user = await _c().register_use_case().execute(body.email, body.username, body.password)
        return _user_out(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    try:
        pair = await _c().login_use_case().execute(body.email, body.password)
        return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        pair = await _c().refresh_use_case().execute(body.refresh_token)
        return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/auth/logout", status_code=204)
async def logout(body: LogoutRequest):
    await _c().logout_use_case().execute(body.refresh_token)


# ── OAuth endpoints ───────────────────────────────────────────────────────────

_OAUTH_CFG = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "scope": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
        "scope": "read:user user:email",
    },
}

_BASE_URL = os.getenv("AUTH_BASE_URL", "http://localhost:8007")
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/auth/oauth/{provider}")
async def oauth_redirect(provider: str):
    cfg = _OAUTH_CFG.get(provider)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown provider")
    redirect_uri = f"{_BASE_URL}/auth/oauth/{provider}/callback"
    url = (
        f"{cfg['auth_url']}?client_id={cfg['client_id']}"
        f"&redirect_uri={redirect_uri}&response_type=code&scope={cfg['scope']}"
    )
    return RedirectResponse(url)


@router.get("/auth/oauth/{provider}/callback", response_model=TokenResponse)
async def oauth_callback(provider: str, code: str):
    cfg = _OAUTH_CFG.get(provider)
    if not cfg:
        raise HTTPException(status_code=404, detail="Unknown provider")

    redirect_uri = f"{_BASE_URL}/auth/oauth/{provider}/callback"

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        headers = {"Accept": "application/json"}
        token_resp = await client.post(cfg["token_url"], data={
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }, headers=headers)
        token_data = token_resp.json()
        provider_token = token_data.get("access_token")
        if not provider_token:
            raise HTTPException(status_code=400, detail="OAuth token exchange failed")

        # Fetch user info
        user_resp = await client.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {provider_token}", "Accept": "application/json"},
        )
        info = user_resp.json()

    # Normalise across providers
    if provider == "google":
        sub, email, username = info["sub"], info["email"], info.get("name", info["email"])
    else:  # github
        sub = str(info["id"])
        email = info.get("email") or f"{info['login']}@github.noreply"
        username = info.get("login", sub)

    try:
        pair = await _c().oauth_login_use_case().execute(
            OAuthProvider(provider), sub, email, username
        )
        # Redirect browser back to frontend with tokens as query params.
        # Frontend /auth/callback page reads them from the URL and stores them.
        return RedirectResponse(
            f"{_FRONTEND_URL}/auth/callback"
            f"?access_token={pair.access_token}&refresh_token={pair.refresh_token}",
            status_code=302,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ── User management endpoints (admin) ─────────────────────────────────────────

@router.get("/users", response_model=list[UserOut])
async def list_users(skip: int = 0, limit: int = 50):
    users = await _c().list_users_use_case().execute(skip=skip, limit=limit)
    return [_user_out(u) for u in users]


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: str):
    user = await _c().get_user_use_case().execute(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, body: UpdateUserRequest):
    user = await _c().get_user_use_case().execute(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.username is not None:
        user.username = body.username
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = UserRole(body.role)
    updated = await _c().update_user_use_case().execute(user)
    return _user_out(updated)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str):
    await _c().delete_user_use_case().execute(user_id)


@router.get("/auth/health")
async def health():
    return {"service": "auth-service", "status": "ok"}
