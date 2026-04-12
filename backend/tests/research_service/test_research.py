"""
Tests for research-service: http_router + use_cases
Covers: prevention (blank query), detection (graph invoke), avoidance (error rate),
        rectification (graph failure, stream failure)
"""
import json
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from research_service.domain.models import ResearchJob, ResearchResult, ResearchStatus, ResearchMode
from research_service.application.use_cases import (
    RunResearchUseCase, StreamResearchUseCase, _build_initial_state, _state_to_result,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_job(**kwargs):
    defaults = dict(
        query_id="qid-1",
        thread_id="thread-1",
        query="What is LangGraph?",
        user_id="user-1",
        budget_limit=5000,
    )
    defaults.update(kwargs)
    return ResearchJob(**defaults)


def make_completed_state(job: ResearchJob) -> dict:
    state = _build_initial_state(job)
    state.update({
        "final_report": "LangGraph is a framework.",
        "mode": "quick",
        "iterations": 1,
        "token_usage": 100,
        "sources": ["https://example.com"],
        "execution_path": ["classify", "quick_mode"],
    })
    return state


# ═══════════════════════════════════════════════════════════════════════════════
# _build_initial_state
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildInitialState:
    def test_all_required_keys_present(self):
        job = make_job()
        state = _build_initial_state(job)
        for key in ("query", "thread_id", "query_id", "user_id", "history",
                    "budget_limit", "context", "intent", "final_report", "sources"):
            assert key in state

    def test_query_propagated(self):
        job = make_job(query="test query")
        assert _build_initial_state(job)["query"] == "test query"

    def test_budget_limit_propagated(self):
        job = make_job(budget_limit=1234)
        assert _build_initial_state(job)["budget_limit"] == 1234


# ═══════════════════════════════════════════════════════════════════════════════
# _state_to_result
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateToResult:
    def test_completed_status_when_report_present(self):
        job = make_job()
        state = make_completed_state(job)
        result = _state_to_result(state, job)
        assert result.status == ResearchStatus.COMPLETED

    def test_clarifying_status_when_question_no_report(self):
        job = make_job()
        state = _build_initial_state(job)
        state["clarification_question"] = "Can you clarify?"
        result = _state_to_result(state, job)
        assert result.status == ResearchStatus.CLARIFYING

    def test_failed_status_when_no_report_no_clarification(self):
        job = make_job()
        state = _build_initial_state(job)
        result = _state_to_result(state, job)
        assert result.status == ResearchStatus.FAILED

    def test_mode_parsed_correctly(self):
        job = make_job()
        state = make_completed_state(job)
        result = _state_to_result(state, job)
        assert result.mode == ResearchMode.QUICK

    def test_unknown_mode_returns_none(self):
        job = make_job()
        state = make_completed_state(job)
        state["mode"] = "unknown"
        result = _state_to_result(state, job)
        assert result.mode is None

    def test_sources_and_execution_path_propagated(self):
        job = make_job()
        state = make_completed_state(job)
        result = _state_to_result(state, job)
        assert result.sources == ["https://example.com"]
        assert "quick_mode" in result.execution_path


# ═══════════════════════════════════════════════════════════════════════════════
# RunResearchUseCase — DETECTION + RECTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunResearchUseCase:
    @pytest.mark.asyncio
    async def test_successful_execution_returns_completed(self):
        job = make_job()
        graph = AsyncMock()
        graph.ainvoke.return_value = make_completed_state(job)
        uc = RunResearchUseCase(graph)
        result = await uc.execute(job)
        assert result.status == ResearchStatus.COMPLETED
        assert result.final_report == "LangGraph is a framework."

    @pytest.mark.asyncio
    async def test_graph_exception_returns_failed_result(self):
        """RECTIFICATION: graph crash → FAILED result, not unhandled exception."""
        job = make_job()
        graph = AsyncMock()
        graph.ainvoke.side_effect = RuntimeError("LLM timeout")
        uc = RunResearchUseCase(graph)
        result = await uc.execute(job)
        assert result.status == ResearchStatus.FAILED
        assert "LLM timeout" in result.final_report

    @pytest.mark.asyncio
    async def test_graph_exception_calls_tracker_rectify(self):
        """RECTIFICATION: tracker.rectify called on graph failure."""
        job = make_job()
        graph = AsyncMock()
        graph.ainvoke.side_effect = RuntimeError("crash")

        mock_tracker = MagicMock()
        mock_tracker.detect = MagicMock()
        # Make detect() a real async context manager that just runs the body
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _detect(op, context=None):
            raise RuntimeError("crash")
            yield  # noqa: unreachable

        mock_tracker.detect.side_effect = _detect

        with patch("research_service.application.use_cases.get_tracker", return_value=mock_tracker):
            uc = RunResearchUseCase(graph)
            result = await uc.execute(job)

        mock_tracker.rectify.assert_called_once()
        call_kwargs = mock_tracker.rectify.call_args
        assert call_kwargs[1]["operation"] == "graph_invoke"

    @pytest.mark.asyncio
    async def test_detection_wraps_graph_invoke(self):
        """DETECTION: tracker.detect is entered for successful graph call."""
        job = make_job()
        graph = AsyncMock()
        graph.ainvoke.return_value = make_completed_state(job)

        detect_entered = []
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _detect(op, context=None):
            detect_entered.append(op)
            yield

        mock_tracker = MagicMock()
        mock_tracker.detect = _detect

        with patch("research_service.application.use_cases.get_tracker", return_value=mock_tracker):
            uc = RunResearchUseCase(graph)
            await uc.execute(job)

        assert "graph_invoke" in detect_entered


# ═══════════════════════════════════════════════════════════════════════════════
# StreamResearchUseCase — DETECTION + RECTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

async def _collect(gen) -> list[dict]:
    events = []
    async for raw in gen:
        events.append(json.loads(raw))
    return events


class TestStreamResearchUseCase:
    @pytest.mark.asyncio
    async def test_emits_node_start_and_end(self):
        job = make_job()
        graph = MagicMock()

        async def _astream(*a, **kw):
            yield {"classify": {"intent": "research"}}

        graph.astream = _astream
        synthesis = AsyncMock()
        synthesis.synthesize_stream = AsyncMock(return_value=_async_iter([]))

        uc = StreamResearchUseCase(graph, synthesis)
        gen = await uc.execute(job)
        events = await _collect(gen)
        types = [e["type"] for e in events]
        assert "node_start" in types
        assert "node_end" in types

    @pytest.mark.asyncio
    async def test_emits_error_event_on_graph_exception(self):
        """RECTIFICATION: stream graph crash → error SSE event, not unhandled exception."""
        job = make_job()
        graph = MagicMock()

        async def _astream(*a, **kw):
            raise RuntimeError("graph exploded")
            yield  # noqa

        graph.astream = _astream
        synthesis = AsyncMock()
        uc = StreamResearchUseCase(graph, synthesis)
        gen = await uc.execute(job)
        events = await _collect(gen)
        assert any(e["type"] == "error" for e in events)
        assert any("graph exploded" in e.get("message", "") for e in events)

    @pytest.mark.asyncio
    async def test_emits_done_event_when_report_present(self):
        job = make_job()
        graph = MagicMock()

        async def _astream(*a, **kw):
            yield {"synthesize": {"final_report": "Report text", "sources": [], "mode": "quick",
                                  "iterations": 1, "token_usage": 50}}

        graph.astream = _astream
        synthesis = AsyncMock()

        async def _synth_stream(**kw):
            yield "Report text"

        synthesis.synthesize_stream = _synth_stream
        uc = StreamResearchUseCase(graph, synthesis)
        gen = await uc.execute(job)
        events = await _collect(gen)
        assert any(e["type"] == "done" for e in events)

    @pytest.mark.asyncio
    async def test_emits_clarification_event(self):
        job = make_job()
        graph = MagicMock()

        async def _astream(*a, **kw):
            yield {"clarify": {"clarification_question": "What do you mean?"}}

        graph.astream = _astream
        synthesis = AsyncMock()
        uc = StreamResearchUseCase(graph, synthesis)
        gen = await uc.execute(job)
        events = await _collect(gen)
        assert any(e["type"] == "clarification" for e in events)

    @pytest.mark.asyncio
    async def test_stream_exception_calls_tracker_rectify(self):
        """RECTIFICATION: tracker.rectify called on stream graph failure."""
        job = make_job()
        graph = MagicMock()

        async def _astream(*a, **kw):
            raise ValueError("stream crash")
            yield  # noqa

        graph.astream = _astream
        synthesis = AsyncMock()

        mock_tracker = MagicMock()
        with patch("research_service.application.use_cases.get_tracker", return_value=mock_tracker):
            uc = StreamResearchUseCase(graph, synthesis)
            gen = await uc.execute(job)
            await _collect(gen)

        mock_tracker.rectify.assert_called_once()
        assert mock_tracker.rectify.call_args[1]["operation"] == "graph_stream"


async def _async_iter(items):
    for item in items:
        yield item


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Router — PREVENTION via FastAPI TestClient
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchHttpRouter:
    @pytest.fixture
    def app(self, tmp_path):
        """Build a minimal FastAPI app with the research router + observability."""
        from fastapi import FastAPI
        from shared.middleware import add_observability

        # Patch container dependencies
        mock_use_case = AsyncMock()
        mock_stream_use_case = AsyncMock()
        mock_conv = AsyncMock()
        mock_conv.ensure_thread = AsyncMock()
        mock_conv.get_history = AsyncMock(return_value=[])

        job_result = ResearchResult(
            query_id="q1", thread_id="t1",
            status=ResearchStatus.COMPLETED,
            final_report="Done.", mode=ResearchMode.QUICK,
        )
        mock_use_case.execute = AsyncMock(return_value=job_result)

        async def _stream_gen():
            yield json.dumps({"type": "done", "sources": [], "mode": "quick",
                              "iterations": 1, "token_usage": 10})

        mock_stream_use_case.execute = AsyncMock(return_value=_stream_gen())

        with patch("research_service.adapters.inbound.http_router.ResearchContainer") as MockC:
            inst = MockC.instance.return_value
            inst.run_research_use_case.return_value = mock_use_case
            inst.stream_research_use_case.return_value = mock_stream_use_case
            inst.conversation_client.return_value = mock_conv

            from research_service.adapters.inbound.http_router import router
            app = FastAPI()
            app.include_router(router)
            add_observability(app, service_name="research-service", log_dir=str(tmp_path))
            yield app

    def test_health_endpoint(self, app):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/research/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "research-service"

    def test_run_requires_auth_header(self, app):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/research/run", json={"query": "test", "thread_id": "t1"})
        assert resp.status_code == 401

    def test_run_with_user_header_succeeds(self, app):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post(
            "/research/run",
            json={"query": "What is AI?", "thread_id": "t1"},
            headers={"X-User-ID": "user-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_stream_requires_auth_header(self, app):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/research/run/stream", json={"query": "test", "thread_id": "t1"})
        assert resp.status_code == 401
