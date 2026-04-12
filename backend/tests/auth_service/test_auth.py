"""
Tests for auth-service: HTTP router + use cases
Covers: registration validation, login, token refresh, logout, observability hooks
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from auth_service.domain.models import User, TokenPair, UserRole, OAuthProvider
from auth_service.application.use_cases import (
    RegisterUseCase, LoginUseCase, RefreshUseCase, LogoutUseCase,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_user(**kwargs):
    defaults = dict(
        id="uid-1", email="test@example.com", username="testuser",
        password_hash="hashed", role=UserRole.USER, is_active=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


def make_token_pair():
    return TokenPair(access_token="access.jwt.token", refresh_token="refresh.jwt.token")


@pytest.fixture
def mock_auth_svc():
    svc = AsyncMock()
    svc.register = AsyncMock(return_value=make_user())
    svc.login = AsyncMock(return_value=make_token_pair())
    svc.refresh = AsyncMock(return_value=make_token_pair())
    svc.logout = AsyncMock()
    return svc


@pytest.fixture
def app(tmp_path, mock_auth_svc):
    from shared.middleware import add_observability
    from auth_service.adapters.inbound.http_router import router

    mock_container = MagicMock()
    mock_container.register_use_case.return_value = RegisterUseCase(mock_auth_svc)
    mock_container.login_use_case.return_value = LoginUseCase(mock_auth_svc)
    mock_container.refresh_use_case.return_value = RefreshUseCase(mock_auth_svc)
    mock_container.logout_use_case.return_value = LogoutUseCase(mock_auth_svc)

    with patch("auth_service.adapters.inbound.http_router._c", return_value=mock_container):
        app = FastAPI()
        app.include_router(router)
        add_observability(app, service_name="auth-service", log_dir=str(tmp_path))
        yield app


@pytest.fixture
def client(app):
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# RegisterUseCase
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterUseCase:
    @pytest.mark.asyncio
    async def test_delegates_to_domain_service(self, mock_auth_svc):
        uc = RegisterUseCase(mock_auth_svc)
        user = await uc.execute("a@b.com", "alice", "pass123")
        mock_auth_svc.register.assert_awaited_once_with("a@b.com", "alice", "pass123")
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_propagates_value_error(self, mock_auth_svc):
        mock_auth_svc.register.side_effect = ValueError("email taken")
        uc = RegisterUseCase(mock_auth_svc)
        with pytest.raises(ValueError, match="email taken"):
            await uc.execute("dup@b.com", "dup", "pass")


# ═══════════════════════════════════════════════════════════════════════════════
# LoginUseCase
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginUseCase:
    @pytest.mark.asyncio
    async def test_returns_token_pair(self, mock_auth_svc):
        uc = LoginUseCase(mock_auth_svc)
        pair = await uc.execute("a@b.com", "pass")
        assert pair.access_token == "access.jwt.token"
        assert pair.refresh_token == "refresh.jwt.token"

    @pytest.mark.asyncio
    async def test_propagates_invalid_credentials(self, mock_auth_svc):
        mock_auth_svc.login.side_effect = ValueError("invalid credentials")
        uc = LoginUseCase(mock_auth_svc)
        with pytest.raises(ValueError, match="invalid credentials"):
            await uc.execute("a@b.com", "wrong")


# ═══════════════════════════════════════════════════════════════════════════════
# RefreshUseCase
# ═══════════════════════════════════════════════════════════════════════════════

class TestRefreshUseCase:
    @pytest.mark.asyncio
    async def test_returns_new_token_pair(self, mock_auth_svc):
        uc = RefreshUseCase(mock_auth_svc)
        pair = await uc.execute("old-refresh-token")
        mock_auth_svc.refresh.assert_awaited_once_with("old-refresh-token")
        assert pair.access_token == "access.jwt.token"

    @pytest.mark.asyncio
    async def test_expired_token_raises(self, mock_auth_svc):
        mock_auth_svc.refresh.side_effect = ValueError("token expired")
        uc = RefreshUseCase(mock_auth_svc)
        with pytest.raises(ValueError, match="token expired"):
            await uc.execute("expired-token")


# ═══════════════════════════════════════════════════════════════════════════════
# LogoutUseCase
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogoutUseCase:
    @pytest.mark.asyncio
    async def test_calls_domain_logout(self, mock_auth_svc):
        uc = LogoutUseCase(mock_auth_svc)
        await uc.execute("refresh-token")
        mock_auth_svc.logout.assert_awaited_once_with("refresh-token")


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Router
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthHttpRouter:
    def test_register_success(self, client):
        resp = client.post("/auth/register", json={
            "email": "new@example.com", "username": "newuser", "password": "secret123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_register_duplicate_returns_400(self, client, mock_auth_svc):
        mock_auth_svc.register.side_effect = ValueError("email already registered")
        resp = client.post("/auth/register", json={
            "email": "dup@example.com", "username": "dup", "password": "pass"
        })
        assert resp.status_code == 400
        assert "email already registered" in resp.json()["detail"]

    def test_login_success(self, client):
        resp = client.post("/auth/login", json={
            "email": "test@example.com", "password": "pass123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "access.jwt.token"
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials_returns_401(self, client, mock_auth_svc):
        mock_auth_svc.login.side_effect = ValueError("invalid credentials")
        resp = client.post("/auth/login", json={
            "email": "test@example.com", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_refresh_success(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "old-token"})
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "access.jwt.token"

    def test_refresh_expired_returns_401(self, client, mock_auth_svc):
        mock_auth_svc.refresh.side_effect = ValueError("expired")
        resp = client.post("/auth/refresh", json={"refresh_token": "expired"})
        assert resp.status_code == 401

    def test_logout_returns_204(self, client):
        resp = client.post("/auth/logout", json={"refresh_token": "some-token"})
        assert resp.status_code == 204

    def test_health_endpoint(self, client):
        resp = client.get("/auth/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "auth-service"

    def test_observability_issues_endpoint(self, client):
        resp = client.get("/health/issues")
        assert resp.status_code == 200
        assert "issues" in resp.json()

    def test_observability_stats_endpoint(self, client):
        resp = client.get("/health/stats")
        assert resp.status_code == 200
        assert "stats" in resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# PREVENTION — input validation at HTTP layer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthPrevention:
    def test_register_missing_email_returns_422(self, client):
        """PREVENTION: Pydantic rejects missing required fields before handler runs."""
        resp = client.post("/auth/register", json={"username": "u", "password": "p"})
        assert resp.status_code == 422

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post("/auth/register", json={
            "email": "not-an-email", "username": "u", "password": "p"
        })
        assert resp.status_code == 422

    def test_login_missing_password_returns_422(self, client):
        resp = client.post("/auth/login", json={"email": "a@b.com"})
        assert resp.status_code == 422

    def test_refresh_missing_token_returns_422(self, client):
        resp = client.post("/auth/refresh", json={})
        assert resp.status_code == 422
