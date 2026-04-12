"""
JWT auth middleware for the API Gateway.
Validates Bearer tokens by calling auth-service over gRPC.
Public paths (health, docs, auth/*) are exempt.

NOTE: BaseHTTPMiddleware cannot raise HTTPException — it bypasses FastAPI's
exception handlers and crashes the ASGI task group. Return JSONResponse directly.
"""
import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from ..adapters.auth_client import AuthServiceClient

logger = logging.getLogger(__name__)

_PUBLIC_PREFIXES = ("/auth/", "/api/v1/health", "/docs", "/openapi", "/redoc")

_auth_client: AuthServiceClient | None = None


def _get_auth_client() -> AuthServiceClient:
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthServiceClient(
            grpc_host=os.getenv("GRPC_AUTH_HOST", "auth-service"),
            grpc_port=int(os.getenv("GRPC_AUTH_GRPC_PORT", "50055")),
        )
    return _auth_client


# BaseHTTPMiddleware early-exit responses bypass Starlette's CORSMiddleware
# send-wrapper, so CORS headers must be added manually here.
_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
}


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=401, headers=_CORS_HEADERS)


def _service_unavailable(detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=503, headers=_CORS_HEADERS)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # CORS preflight — let CORSMiddleware handle it, no auth required
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public paths ("/" matched exactly to avoid catch-all on every path)
        if path == "/" or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized("Missing token")

        token = auth_header[7:]
        try:
            result = await _get_auth_client().validate_token(token)
        except Exception:
            logger.exception("Auth service gRPC call failed for path %s", path)
            return _service_unavailable("Auth service unavailable")

        if not result.valid:
            logger.warning("Token validation failed for path %s: %s", path, result.error)
            return _unauthorized(result.error or "Invalid token")

        # Inject user info into request state for downstream handlers
        request.state.user_id = result.user_id
        request.state.email = result.email
        request.state.role = result.role

        return await call_next(request)
