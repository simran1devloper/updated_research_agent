"""
Tests for api-gateway: health router + JWT auth middleware
Covers: health aggregation, auth bypass for public paths, token validation,
        observability middleware integration
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


# ═══════════════════════════════════════════════════════════════════════════════
# Health Router
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthRouter:
    @pytest.fixture
    def app(self, tmp_path):
        from shared.middleware import add_observability
        from api_gateway.routers.health import router

        mock_container = MagicMock()

        def _make_client(status="ok"):
            c = AsyncMock()
            c.health = AsyncMock(return_value={"status": status})
            return c

        mock_container.intent_client.return_value = _make_client()
        mock_container.memory_client.return_value = _make_client()
        mock_container.search_client.return_value = _make_client()
        mock_container.synthesis_client.return_value = _make_client()
        mock_container.research_client.return_value = _make_client()

        with patch("api_gateway.routers.health.GatewayContainer") as MockC:
            MockC.instance.return_value = mock_container
            app = FastAPI()
            app.include_router(router)
            add_observability(app, service_name="api-gateway", log_dir=str(tmp_path))
            yield app

    def test_all_services_ok(self, app):
        client = TestClient(app)
        resp = client.get("/api/v1/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"] == "ok"
        assert all(v == "ok" for v in data["services"].values())

    def test_degraded_when_one_service_unreachable(self, tmp_path):
        from shared.middleware import add_observability
        from api_gateway.routers.health import router

        mock_container = MagicMock()

        def _ok_client():
            c = AsyncMock()
            c.health = AsyncMock()
            return c

        def _bad_client():
            c = AsyncMock()
            c.health = AsyncMock(side_effect=ConnectionError("unreachable"))
            return c

        mock_container.intent_client.return_value = _ok_client()
        mock_container.memory_client.return_value = _ok_client()
        mock_container.search_client.return_value = _bad_client()
        mock_container.synthesis_client.return_value = _ok_client()
        mock_container.research_client.return_value = _ok_client()

        with patch("api_gateway.routers.health.GatewayContainer") as MockC:
            MockC.instance.return_value = mock_container
            app = FastAPI()
            app.include_router(router)
            add_observability(app, service_name="api-gateway-deg", log_dir=str(tmp_path))
            client = TestClient(app)
            resp = client.get("/api/v1/health/")
            assert resp.status_code == 200
            data = resp.json()
            assert data["overall"] == "degraded"
            assert data["services"]["search-service"] == "unreachable"

    def test_observability_endpoints_available(self, app):
        client = TestClient(app)
        assert client.get("/health/issues").status_code == 200
        assert client.get("/health/stats").status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# JWT Auth Middleware
# ═══════════════════════════════════════════════════════════════════════════════

class TestJWTAuthMiddleware:
    @pytest.fixture
    def app_with_auth(self, tmp_path):
        from shared.middleware import add_observability
        from api_gateway.middleware.auth import JWTAuthMiddleware
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
        app.add_middleware(JWTAuthMiddleware)
        add_observability(app, service_name="gw-auth-test", log_dir=str(tmp_path))

        @app.get("/api/v1/protected")
        async def protected():
            return {"ok": True}

        @app.get("/api/v1/health/")
        async def health():
            return {"ok": True}

        @app.get("/")
        async def root():
            return {"ok": True}

        yield app

    def test_public_health_path_bypasses_auth(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get("/api/v1/health/")
        assert resp.status_code == 200

    def test_root_path_bypasses_auth(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_missing_token_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get("/api/v1/protected")
        assert resp.status_code == 401
        assert "Missing token" in resp.json()["detail"]

    def test_malformed_token_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get("/api/v1/protected", headers={"Authorization": "NotBearer token"})
        assert resp.status_code == 401

    def test_valid_token_passes_through(self, app_with_auth):
        mock_result = MagicMock()
        mock_result.valid = True
        mock_result.user_id = "uid-1"
        mock_result.email = "u@example.com"
        mock_result.role = "user"

        mock_auth_client = AsyncMock()
        mock_auth_client.validate_token = AsyncMock(return_value=mock_result)

        with patch("api_gateway.middleware.auth._get_auth_client", return_value=mock_auth_client):
            client = TestClient(app_with_auth)
            resp = client.get("/api/v1/protected", headers={"Authorization": "Bearer valid.token"})
        assert resp.status_code == 200

    def test_invalid_token_returns_401(self, app_with_auth):
        mock_result = MagicMock()
        mock_result.valid = False
        mock_result.error = "Token expired"

        mock_auth_client = AsyncMock()
        mock_auth_client.validate_token = AsyncMock(return_value=mock_result)

        with patch("api_gateway.middleware.auth._get_auth_client", return_value=mock_auth_client):
            client = TestClient(app_with_auth)
            resp = client.get("/api/v1/protected", headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code == 401
        assert "Token expired" in resp.json()["detail"]

    def test_auth_service_unavailable_returns_503(self, app_with_auth):
        """AVOIDANCE: auth service down → 503, not 500 crash."""
        mock_auth_client = AsyncMock()
        mock_auth_client.validate_token = AsyncMock(side_effect=ConnectionError("gRPC down"))

        with patch("api_gateway.middleware.auth._get_auth_client", return_value=mock_auth_client):
            client = TestClient(app_with_auth)
            resp = client.get("/api/v1/protected", headers={"Authorization": "Bearer any.token"})
        assert resp.status_code == 503

    def test_options_preflight_bypasses_auth(self, app_with_auth):
        """PREVENTION: CORS preflight must never be blocked by auth."""
        client = TestClient(app_with_auth)
        resp = client.options("/api/v1/protected", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        })
        # Should not be 401
        assert resp.status_code != 401
