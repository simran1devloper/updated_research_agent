"""
Service Tracker — covers the full issue lifecycle:

  1. PREVENTION  — validate inputs / preconditions before execution
  2. DETECTION   — capture errors, anomalies, slow calls as they happen
  3. AVOIDANCE   — circuit-breaker style counters; emit warnings before hard failure
  4. RECTIFICATION — structured error records with context for post-mortem / auto-retry

Usage:
    from shared.tracker import ServiceTracker
    tracker = ServiceTracker("research-service", logger)

    # prevention
    tracker.prevent("query must not be empty", condition=bool(query), context={"query": query})

    # detection (wrap a call)
    async with tracker.detect("llm_call", context={"model": "ministral"}):
        result = await llm.invoke(prompt)

    # avoidance (check thresholds)
    tracker.avoid("llm_error_rate", current=err_rate, threshold=0.3)

    # rectification (record + optionally re-raise)
    tracker.rectify(exc, operation="llm_call", context={...})
"""
from __future__ import annotations

import time
import traceback
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import logging


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class IssueRecord:
    stage: str          # prevention | detection | avoidance | rectification
    service: str
    operation: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exc_type: str = ""
    exc_trace: str = ""


# ── Tracker ─────────────────────────────────────────────────────────────────

class ServiceTracker:
    """
    Lightweight in-process tracker.  All records are also emitted through the
    supplied logger so they land in the rotating JSON log file.
    """

    def __init__(self, service_name: str, logger: logging.Logger) -> None:
        self.service = service_name
        self._log = logger
        # rolling window of last 200 issue records (in-memory, for /health/issues)
        self._records: deque[IssueRecord] = deque(maxlen=200)
        # per-operation error counters for avoidance checks
        self._error_counts: dict[str, int] = defaultdict(int)
        self._call_counts: dict[str, int] = defaultdict(int)

    # ── 1. PREVENTION ───────────────────────────────────────────────────────

    def prevent(
        self,
        rule: str,
        *,
        condition: bool,
        context: dict[str, Any] | None = None,
        raise_on_fail: bool = True,
    ) -> bool:
        """
        Assert a precondition before an operation runs.
        Returns True if condition passes, False (or raises) if it fails.
        """
        if condition:
            return True
        rec = IssueRecord(
            stage="prevention",
            service=self.service,
            operation=rule,
            message=f"Prevention rule FAILED: {rule}",
            context=context or {},
        )
        self._records.append(rec)
        self._log.warning(rec.message, extra={"tracker": rec.__dict__})
        if raise_on_fail:
            raise ValueError(f"[{self.service}] Prevention failed: {rule}")
        return False

    # ── 2. DETECTION ────────────────────────────────────────────────────────

    @asynccontextmanager
    async def detect(self, operation: str, context: dict[str, Any] | None = None):
        """
        Async context manager that measures latency and captures any exception.
        Logs a WARNING for slow calls (>5 s) and ERROR for exceptions.
        """
        ctx = context or {}
        start = time.perf_counter()
        self._call_counts[operation] += 1
        try:
            yield
            elapsed = time.perf_counter() - start
            if elapsed > 5.0:
                rec = IssueRecord(
                    stage="detection",
                    service=self.service,
                    operation=operation,
                    message=f"Slow operation detected: {operation} took {elapsed:.2f}s",
                    context={**ctx, "latency_s": round(elapsed, 3)},
                )
                self._records.append(rec)
                self._log.warning(rec.message, extra={"tracker": rec.__dict__})
            else:
                self._log.debug(
                    "Operation OK: %s (%.3fs)", operation, elapsed,
                    extra={"service": self.service, "latency_s": round(elapsed, 3)},
                )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            self._error_counts[operation] += 1
            rec = IssueRecord(
                stage="detection",
                service=self.service,
                operation=operation,
                message=f"Exception detected in {operation}: {exc}",
                context={**ctx, "latency_s": round(elapsed, 3)},
                exc_type=type(exc).__name__,
                exc_trace=traceback.format_exc(),
            )
            self._records.append(rec)
            self._log.error(rec.message, extra={"tracker": rec.__dict__})
            raise

    # ── 3. AVOIDANCE ────────────────────────────────────────────────────────

    def avoid(
        self,
        metric: str,
        *,
        current: float,
        threshold: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a WARNING when a metric approaches a dangerous threshold.
        Does NOT raise — it's a proactive signal to act before failure.
        """
        if current >= threshold:
            rec = IssueRecord(
                stage="avoidance",
                service=self.service,
                operation=metric,
                message=(
                    f"Avoidance alert: {metric} = {current:.3f} "
                    f"exceeds threshold {threshold:.3f}"
                ),
                context={**(context or {}), "current": current, "threshold": threshold},
            )
            self._records.append(rec)
            self._log.warning(rec.message, extra={"tracker": rec.__dict__})

    def check_error_rate(self, operation: str, threshold: float = 0.3) -> None:
        """Convenience: compute error rate for an operation and call avoid()."""
        calls = self._call_counts.get(operation, 0)
        errors = self._error_counts.get(operation, 0)
        if calls == 0:
            return
        rate = errors / calls
        self.avoid(
            f"{operation}_error_rate",
            current=rate,
            threshold=threshold,
            context={"calls": calls, "errors": errors},
        )

    # ── 4. RECTIFICATION ────────────────────────────────────────────────────

    def rectify(
        self,
        exc: Exception,
        *,
        operation: str,
        context: dict[str, Any] | None = None,
        reraise: bool = False,
    ) -> IssueRecord:
        """
        Record a structured error with full context for post-mortem / retry logic.
        Returns the IssueRecord so callers can attach it to a response or retry queue.
        """
        rec = IssueRecord(
            stage="rectification",
            service=self.service,
            operation=operation,
            message=f"Rectification needed for {operation}: {exc}",
            context=context or {},
            exc_type=type(exc).__name__,
            exc_trace=traceback.format_exc(),
        )
        self._records.append(rec)
        self._log.error(rec.message, extra={"tracker": rec.__dict__})
        if reraise:
            raise exc
        return rec

    # ── Inspection ──────────────────────────────────────────────────────────

    def recent_issues(self, stage: str | None = None, limit: int = 50) -> list[dict]:
        """Return recent issue records, optionally filtered by stage."""
        records = list(self._records)
        if stage:
            records = [r for r in records if r.stage == stage]
        return [r.__dict__ for r in records[-limit:]]

    def stats(self) -> dict[str, Any]:
        """Return per-operation call/error counts."""
        return {
            op: {
                "calls": self._call_counts[op],
                "errors": self._error_counts[op],
                "error_rate": round(self._error_counts[op] / self._call_counts[op], 3)
                if self._call_counts[op] else 0.0,
            }
            for op in self._call_counts
        }
