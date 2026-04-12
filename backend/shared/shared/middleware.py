"""
ObservabilityMiddleware — drop-in FastAPI/Starlette middleware.
Automatically tracks every inbound HTTP request:
  - logs method, path, status, latency
  - records slow requests (>5 s) as detection issues
  - records 5xx responses as rectification issues
  - exposes GET /health/issues and GET /health/stats endpoints

Usage in any service main.py:
    from shared.middleware import add_observability
    add_observability(app, service_name="research-service")
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .logger import get_logger
from .tracker import ServiceTracker


# Module-level registry so routers can access the tracker
_trackers: dict[str, ServiceTracker] = {}


def get_tracker(service_name: str) -> ServiceTracker | None:
    return _trackers.get(service_name)


class _RequestTrackingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str, tracker: ServiceTracker, logger) -> None:
        super().__init__(app)
        self._service = service_name
        self._tracker = tracker
        self._log = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            self._tracker.rectify(
                exc,
                operation=f"{method} {path}",
                context={"latency_s": round(elapsed, 3)},
            )
            raise

        elapsed = time.perf_counter() - start
        status = response.status_code
        ctx = {"method": method, "path": path, "status": status, "latency_s": round(elapsed, 3)}

        # ── Detection: slow request ─────────────────────────────────────────
        if elapsed > 5.0:
            self._tracker._records.append(  # type: ignore[attr-defined]
                __import__("shared.tracker", fromlist=["IssueRecord"]).IssueRecord(
                    stage="detection",
                    service=self._service,
                    operation=f"{method} {path}",
                    message=f"Slow request: {method} {path} took {elapsed:.2f}s",
                    context=ctx,
                )
            )
            self._log.warning("Slow request: %s %s %.2fs", method, path, elapsed,
                               extra={"tracker_ctx": ctx})

        # ── Rectification: server errors ────────────────────────────────────
        elif status >= 500:
            from .tracker import IssueRecord
            self._tracker._records.append(
                IssueRecord(
                    stage="rectification",
                    service=self._service,
                    operation=f"{method} {path}",
                    message=f"HTTP {status} on {method} {path}",
                    context=ctx,
                )
            )
            self._log.error("HTTP %s: %s %s (%.3fs)", status, method, path, elapsed,
                            extra={"tracker_ctx": ctx})

        else:
            self._log.info("%s %s %s %.3fs", method, path, status, elapsed,
                           extra={"tracker_ctx": ctx})

        return response


def add_observability(app: FastAPI, service_name: str, log_dir: str = "logs") -> ServiceTracker:
    # Resolve log_dir relative to CWD (run.sh always cds into the service dir first)
    """
    Attach logger + tracker + middleware to a FastAPI app.
    Also mounts /health/issues and /health/stats endpoints.
    Returns the ServiceTracker so the service can use it directly.
    """
    logger = get_logger(service_name, log_dir=log_dir)
    tracker = ServiceTracker(service_name, logger)
    _trackers[service_name] = tracker

    app.add_middleware(_RequestTrackingMiddleware,
                       service_name=service_name,
                       tracker=tracker,
                       logger=logger)

    # ── Observability endpoints ─────────────────────────────────────────────
    obs_router = APIRouter(prefix="/health", tags=["observability"])

    @obs_router.get("/issues")
    async def issues(stage: str | None = None, limit: int = 50):
        """Recent tracked issues, optionally filtered by stage."""
        return {"service": service_name, "issues": tracker.recent_issues(stage=stage, limit=limit)}

    @obs_router.get("/stats")
    async def stats():
        """Per-operation call/error counts and error rates."""
        return {"service": service_name, "stats": tracker.stats()}

    app.include_router(obs_router)
    logger.info("Observability attached to %s", service_name)
    return tracker
