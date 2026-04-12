"""
Tests for shared/logger.py, shared/tracker.py, shared/middleware.py
Covers: prevention, detection, avoidance, rectification + HTTP middleware
"""
import asyncio
import logging
import os
import sys
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../shared"))

from shared.logger import get_logger
from shared.tracker import ServiceTracker, IssueRecord


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def logger(tmp_path):
    name = f"test-svc-{id(tmp_path)}"
    return get_logger(name, log_dir=str(tmp_path))


@pytest.fixture
def tracker(logger):
    return ServiceTracker("test-service", logger)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogger:
    def test_returns_logger_instance(self, tmp_path):
        log = get_logger("svc-a", log_dir=str(tmp_path))
        assert isinstance(log, logging.Logger)

    def test_idempotent_second_call(self, tmp_path):
        log1 = get_logger("svc-b", log_dir=str(tmp_path))
        log2 = get_logger("svc-b", log_dir=str(tmp_path))
        assert log1 is log2

    def test_creates_log_file(self, tmp_path):
        log = get_logger("svc-c", log_dir=str(tmp_path))
        log.info("hello")
        assert (tmp_path / "app.log").exists()

    def test_json_output_in_file(self, tmp_path):
        import json
        log = get_logger("svc-d", log_dir=str(tmp_path))
        log.info("test-message", extra={"custom_key": "custom_val"})
        lines = (tmp_path / "app.log").read_text().strip().splitlines()
        assert lines, "log file is empty"
        payload = json.loads(lines[-1])
        assert payload["msg"] == "test-message"
        assert payload["level"] == "INFO"
        assert payload["custom_key"] == "custom_val"

    def test_exception_serialised(self, tmp_path):
        import json
        log = get_logger("svc-e", log_dir=str(tmp_path))
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("caught")
        lines = (tmp_path / "app.log").read_text().strip().splitlines()
        payload = json.loads(lines[-1])
        assert "exc" in payload
        assert "ValueError" in payload["exc"]


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER — 1. PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerPrevention:
    def test_passes_when_condition_true(self, tracker):
        assert tracker.prevent("non-empty", condition=True) is True

    def test_raises_when_condition_false(self, tracker):
        with pytest.raises(ValueError, match="Prevention failed"):
            tracker.prevent("non-empty", condition=False)

    def test_no_raise_when_raise_on_fail_false(self, tracker):
        result = tracker.prevent("rule", condition=False, raise_on_fail=False)
        assert result is False

    def test_records_issue_on_failure(self, tracker):
        tracker.prevent("rule", condition=False, raise_on_fail=False)
        issues = tracker.recent_issues(stage="prevention")
        assert len(issues) == 1
        assert issues[0]["stage"] == "prevention"
        assert "FAILED" in issues[0]["message"]

    def test_context_stored_in_record(self, tracker):
        tracker.prevent("ctx-rule", condition=False, context={"key": "val"}, raise_on_fail=False)
        issues = tracker.recent_issues(stage="prevention")
        assert issues[-1]["context"]["key"] == "val"

    def test_no_record_on_pass(self, tracker):
        tracker.prevent("ok-rule", condition=True)
        assert tracker.recent_issues(stage="prevention") == []


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER — 2. DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerDetection:
    @pytest.mark.asyncio
    async def test_successful_operation_increments_call_count(self, tracker):
        async with tracker.detect("op1"):
            pass
        assert tracker._call_counts["op1"] == 1

    @pytest.mark.asyncio
    async def test_exception_increments_error_count(self, tracker):
        with pytest.raises(RuntimeError):
            async with tracker.detect("op2"):
                raise RuntimeError("fail")
        assert tracker._error_counts["op2"] == 1
        assert tracker._call_counts["op2"] == 1

    @pytest.mark.asyncio
    async def test_exception_creates_detection_record(self, tracker):
        with pytest.raises(RuntimeError):
            async with tracker.detect("op3", context={"x": 1}):
                raise RuntimeError("boom")
        issues = tracker.recent_issues(stage="detection")
        assert any("op3" in r["operation"] for r in issues)
        assert any(r["exc_type"] == "RuntimeError" for r in issues)

    @pytest.mark.asyncio
    async def test_slow_operation_creates_warning_record(self, tracker):
        with patch("time.perf_counter", side_effect=[0.0, 6.0]):
            async with tracker.detect("slow-op"):
                pass
        issues = tracker.recent_issues(stage="detection")
        assert any("slow-op" in r["operation"] for r in issues)

    @pytest.mark.asyncio
    async def test_exception_reraises(self, tracker):
        with pytest.raises(ValueError):
            async with tracker.detect("reraise-op"):
                raise ValueError("must propagate")

    @pytest.mark.asyncio
    async def test_context_attached_to_record(self, tracker):
        with pytest.raises(KeyError):
            async with tracker.detect("ctx-op", context={"user": "alice"}):
                raise KeyError("missing")
        issues = tracker.recent_issues(stage="detection")
        rec = next(r for r in issues if r["operation"] == "ctx-op")
        assert rec["context"]["user"] == "alice"


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER — 3. AVOIDANCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerAvoidance:
    def test_no_record_below_threshold(self, tracker):
        tracker.avoid("metric", current=0.1, threshold=0.3)
        assert tracker.recent_issues(stage="avoidance") == []

    def test_record_at_threshold(self, tracker):
        tracker.avoid("metric", current=0.3, threshold=0.3)
        issues = tracker.recent_issues(stage="avoidance")
        assert len(issues) == 1
        assert issues[0]["context"]["current"] == 0.3

    def test_record_above_threshold(self, tracker):
        tracker.avoid("metric", current=0.9, threshold=0.3)
        issues = tracker.recent_issues(stage="avoidance")
        assert len(issues) == 1

    @pytest.mark.asyncio
    async def test_check_error_rate_triggers_avoidance(self, tracker):
        # 2 errors out of 2 calls = 100% error rate > 30% threshold
        for _ in range(2):
            with pytest.raises(RuntimeError):
                async with tracker.detect("flaky"):
                    raise RuntimeError("err")
        tracker.check_error_rate("flaky", threshold=0.3)
        issues = tracker.recent_issues(stage="avoidance")
        assert any("flaky" in r["operation"] for r in issues)

    def test_check_error_rate_no_calls_is_noop(self, tracker):
        tracker.check_error_rate("never-called")
        assert tracker.recent_issues(stage="avoidance") == []


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER — 4. RECTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerRectification:
    def test_returns_issue_record(self, tracker):
        rec = tracker.rectify(ValueError("oops"), operation="save")
        assert isinstance(rec, IssueRecord)
        assert rec.stage == "rectification"
        assert rec.exc_type == "ValueError"

    def test_record_stored_in_buffer(self, tracker):
        tracker.rectify(RuntimeError("db down"), operation="db_write")
        issues = tracker.recent_issues(stage="rectification")
        assert len(issues) == 1
        assert "db_write" in issues[0]["operation"]

    def test_reraise_flag(self, tracker):
        with pytest.raises(OSError):
            tracker.rectify(OSError("disk full"), operation="write", reraise=True)

    def test_context_in_record(self, tracker):
        tracker.rectify(Exception("x"), operation="op", context={"retry": 3})
        issues = tracker.recent_issues(stage="rectification")
        assert issues[-1]["context"]["retry"] == 3

    def test_exc_trace_populated(self, tracker):
        try:
            raise TypeError("type err")
        except TypeError as e:
            rec = tracker.rectify(e, operation="typed-op")
        assert "TypeError" in rec.exc_trace


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER — Inspection helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerInspection:
    def test_recent_issues_limit(self, tracker):
        for i in range(10):
            tracker.rectify(Exception(str(i)), operation=f"op{i}")
        assert len(tracker.recent_issues(limit=5)) == 5

    def test_recent_issues_stage_filter(self, tracker):
        tracker.prevent("r1", condition=False, raise_on_fail=False)
        tracker.rectify(Exception("e"), operation="r2")
        assert all(r["stage"] == "prevention" for r in tracker.recent_issues(stage="prevention"))

    def test_stats_returns_correct_counts(self, tracker):
        asyncio.get_event_loop().run_until_complete(_run_stats_ops(tracker))
        s = tracker.stats()
        assert s["stats-op"]["calls"] == 3
        assert s["stats-op"]["errors"] == 1
        assert abs(s["stats-op"]["error_rate"] - 0.333) < 0.01

    def test_ring_buffer_max_200(self, tracker):
        for i in range(250):
            tracker.rectify(Exception(str(i)), operation="flood")
        assert len(tracker._records) == 200


async def _run_stats_ops(tracker):
    for i in range(3):
        try:
            async with tracker.detect("stats-op"):
                if i == 1:
                    raise RuntimeError("one fail")
        except RuntimeError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE — add_observability + HTTP tracking
# ═══════════════════════════════════════════════════════════════════════════════

class TestObservabilityMiddleware:
    def test_add_observability_returns_tracker(self, tmp_path):
        from fastapi import FastAPI
        from shared.middleware import add_observability, get_tracker
        app = FastAPI()
        t = add_observability(app, service_name="mw-test", log_dir=str(tmp_path))
        assert isinstance(t, ServiceTracker)
        assert get_tracker("mw-test") is t

    def test_health_issues_endpoint_registered(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from shared.middleware import add_observability
        app = FastAPI()
        add_observability(app, service_name="mw-issues", log_dir=str(tmp_path))
        client = TestClient(app)
        resp = client.get("/health/issues")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "mw-issues"
        assert "issues" in data

    def test_health_stats_endpoint_registered(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from shared.middleware import add_observability
        app = FastAPI()
        add_observability(app, service_name="mw-stats", log_dir=str(tmp_path))
        client = TestClient(app)
        resp = client.get("/health/stats")
        assert resp.status_code == 200
        assert "stats" in resp.json()

    def test_middleware_logs_normal_request(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from shared.middleware import add_observability
        app = FastAPI()
        add_observability(app, service_name="mw-log", log_dir=str(tmp_path))

        @app.get("/ping")
        async def ping():
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200

    def test_middleware_records_5xx_as_rectification(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from shared.middleware import add_observability, get_tracker
        app = FastAPI()
        t = add_observability(app, service_name="mw-5xx", log_dir=str(tmp_path))

        @app.get("/boom")
        async def boom():
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="server error")

        client = TestClient(app, raise_server_exceptions=False)
        client.get("/boom")
        issues = t.recent_issues(stage="rectification")
        assert any("500" in r["message"] or "/boom" in r["operation"] for r in issues)

    def test_middleware_records_slow_request_as_detection(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from shared.middleware import add_observability, get_tracker
        import shared.middleware as mw_module

        app = FastAPI()
        t = add_observability(app, service_name="mw-slow", log_dir=str(tmp_path))

        @app.get("/slow")
        async def slow():
            return {"ok": True}

        # Patch perf_counter to simulate 6s elapsed
        call_count = 0
        original = time.perf_counter

        def fake_counter():
            nonlocal call_count
            call_count += 1
            return 0.0 if call_count == 1 else 6.0

        with patch("time.perf_counter", side_effect=fake_counter):
            client = TestClient(app)
            client.get("/slow")

        issues = t.recent_issues(stage="detection")
        assert any("/slow" in r["operation"] for r in issues)
