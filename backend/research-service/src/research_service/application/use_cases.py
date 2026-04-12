"""Application use-case for the Research Service orchestrator."""
import asyncio
import uuid
import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.ports import ISynthesisClientPort

from ..domain.models import ResearchJob, ResearchResult, ResearchStatus, ResearchMode
from shared.middleware import get_tracker

logger = logging.getLogger(__name__)


class RunResearchUseCase:
    def __init__(self, compiled_graph) -> None:
        self._graph = compiled_graph

    async def execute(self, job: ResearchJob) -> ResearchResult:
        initial_state = _build_initial_state(job)
        config = {"configurable": {"thread_id": job.thread_id}}
        tracker = get_tracker("research-service")
        ctx = {"query_id": job.query_id, "thread_id": job.thread_id, "user_id": job.user_id}
        try:
            if tracker:
                async with tracker.detect("graph_invoke", context=ctx):
                    final_state = await self._graph.ainvoke(initial_state, config=config)
            else:
                final_state = await self._graph.ainvoke(initial_state, config=config)
            return _state_to_result(final_state, job)
        except Exception as exc:
            logger.error("Research workflow failed: %s", exc, exc_info=True)
            if tracker:
                tracker.rectify(exc, operation="graph_invoke", context=ctx)
            return ResearchResult(
                query_id=job.query_id,
                thread_id=job.thread_id,
                status=ResearchStatus.FAILED,
                final_report=f"Research failed: {exc}",
            )


class StreamResearchUseCase:
    """Streams SSE events: node_start/node_end per graph node, then live
    token chunks piped directly from synthesis-service SSE."""

    def __init__(self, compiled_graph, synthesis_port: "ISynthesisClientPort", conversation_port=None) -> None:
        self._graph = compiled_graph
        self._synthesis_port = synthesis_port
        self._conversation_port = conversation_port

    async def execute(self, job: ResearchJob) -> AsyncIterator[str]:
        initial_state = _build_initial_state(job)
        config = {"configurable": {"thread_id": job.thread_id}}

        async def _gen():
            tracker = get_tracker("research-service")
            ctx = {"thread_id": job.thread_id, "user_id": job.user_id}
            try:
                accumulated: dict = dict(initial_state)

                async for snapshot in self._graph.astream(
                    initial_state, config=config, stream_mode="updates"
                ):
                    for node_name, updates in snapshot.items():
                        # Emit node_start, yield to event loop so frontend renders it
                        yield json.dumps({"type": "node_start", "node": node_name})
                        await asyncio.sleep(0)  # flush before blocking work

                        accumulated.update(updates)

                        # For synthesize / quick_mode nodes: stream tokens live
                        if node_name in ("synthesize", "quick_mode"):
                            yield json.dumps({"type": "report_start"})
                            full_report = ""
                            async for chunk in self._synthesis_port.synthesize_stream(
                                query=accumulated.get("query", ""),
                                research_data=accumulated.get("research_data") or [
                                    {"content": c, "source": "memory", "url": ""}
                                    for c in accumulated.get("context", [])
                                ] or [{"content": accumulated.get("query", ""), "source": "direct", "url": ""}],
                                history=accumulated.get("history", []),
                                gaps=accumulated.get("gaps", []),
                            ):
                                full_report += chunk
                                yield json.dumps({"type": "token", "chunk": chunk})
                            # Patch accumulated state so formatter has the report
                            accumulated["final_report"] = full_report

                        yield json.dumps({"type": "node_end", "node": node_name})

                report: str = accumulated.get("final_report", "")
                clarification: str = accumulated.get("clarification_question", "")

                if report:
                    yield json.dumps({
                        "type": "done",
                        "sources": accumulated.get("sources", []),
                        "mode": accumulated.get("mode", ""),
                        "iterations": accumulated.get("iterations", 0),
                        "token_usage": accumulated.get("token_usage", 0),
                    })
                    # Persist to conversation history (formatter node doesn't run in stream mode)
                    thread_id = job.thread_id
                    if thread_id and self._conversation_port:
                        await self._conversation_port.append_message(thread_id, "user", job.query)
                        await self._conversation_port.append_message(thread_id, "assistant", report)
                elif clarification:
                    yield json.dumps({"type": "clarification", "question": clarification})
                else:
                    yield json.dumps({"type": "error", "message": "No report generated."})

            except Exception as exc:
                logger.error("Stream research failed: %s", exc, exc_info=True)
                if tracker:
                    tracker.rectify(exc, operation="graph_stream", context=ctx)
                yield json.dumps({"type": "error", "message": str(exc)})

        return _gen()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_initial_state(job: ResearchJob) -> dict:
    return {
        "query": job.query,
        "thread_id": job.thread_id,
        "query_id": job.query_id or str(uuid.uuid4()),
        "user_id": job.user_id,
        "history": job.history,
        "budget_limit": job.budget_limit,
        "context": [],
        "intent": "",
        "is_clarified": False,
        "clarification_question": "",
        "confidence_score": 0.0,
        "mode": "",
        "research_data": [],
        "iterations": 0,
        "gaps": [],
        "research_confidence_score": 0.0,
        "final_report": "",
        "token_usage": 0,
        "sources": [],
        "execution_path": [],
    }


def _state_to_result(final_state: dict, job: ResearchJob) -> ResearchResult:
    if final_state.get("clarification_question") and not final_state.get("final_report"):
        status = ResearchStatus.CLARIFYING
    elif final_state.get("final_report"):
        status = ResearchStatus.COMPLETED
    else:
        status = ResearchStatus.FAILED

    mode_str = final_state.get("mode", "")
    mode = ResearchMode(mode_str) if mode_str in ("quick", "deep") else None

    return ResearchResult(
        query_id=final_state.get("query_id", job.query_id),
        thread_id=job.thread_id,
        status=status,
        mode=mode,
        final_report=final_state.get("final_report", ""),
        clarification_question=final_state.get("clarification_question", ""),
        token_usage=final_state.get("token_usage", 0),
        iterations=final_state.get("iterations", 0),
        sources=final_state.get("sources", []),
        execution_path=final_state.get("execution_path", []),
    )


def _safe_output(output) -> dict:
    """Extract only serialisable scalar fields from a node output dict."""
    if not isinstance(output, dict):
        return {}
    safe = {}
    for k, v in output.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe[k] = v
        elif isinstance(v, list) and all(isinstance(i, str) for i in v):
            safe[k] = v
    return safe