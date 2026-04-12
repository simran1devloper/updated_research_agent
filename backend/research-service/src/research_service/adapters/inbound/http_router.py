"""Inbound HTTP adapter for the Research Service."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from shared.models import ResearchRequest, ResearchResponse, ResearchStatus, ResearchMode, HealthResponse
from shared.middleware import get_tracker

from ...domain.models import ResearchJob
from ...application.use_cases import RunResearchUseCase, StreamResearchUseCase
from ...adapters.outbound.conversation_client import ConversationServiceClient
from ...container import ResearchContainer

router = APIRouter(prefix="/research", tags=["research"])


def _get_use_case() -> RunResearchUseCase:
    return ResearchContainer.instance().run_research_use_case()


def _get_stream_use_case() -> StreamResearchUseCase:
    return ResearchContainer.instance().stream_research_use_case()


def _get_conv_client() -> ConversationServiceClient:
    return ResearchContainer.instance().conversation_client()


def _user_id(request: Request) -> str:
    # Prefer the trusted internal header forwarded by the gateway,
    # fall back to request.state for direct/test calls.
    uid = request.headers.get("X-User-ID", "") or getattr(request.state, "user_id", "")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="research-service")


@router.post("/run", response_model=ResearchResponse)
async def run_research(
    body: ResearchRequest,
    request: Request,
    use_case: RunResearchUseCase = Depends(_get_use_case),
) -> ResearchResponse:
    user_id = _user_id(request)
    tracker = get_tracker("research-service")

    # PREVENTION: query must not be blank
    if tracker:
        tracker.prevent("query-non-empty", condition=bool(body.query and body.query.strip()),
                        context={"user_id": user_id, "thread_id": body.thread_id})

    conv = _get_conv_client()

    # Ensure thread exists and load persisted history
    if body.thread_id and user_id:
        await conv.ensure_thread(body.thread_id, user_id, title=body.query[:60])
        history = await conv.get_history(body.thread_id, limit=20)
    else:
        history = body.history

    job = ResearchJob(
        query_id=str(uuid.uuid4()),
        thread_id=body.thread_id,
        query=body.query,
        user_id=user_id,
        history=history,
        budget_limit=body.budget_limit,
    )
    ctx = {"query_id": job.query_id, "user_id": user_id, "thread_id": body.thread_id}
    if tracker:
        async with tracker.detect("run_research", context=ctx):
            result = await use_case.execute(job)
    else:
        result = await use_case.execute(job)
    if tracker:
        tracker.check_error_rate("run_research")
    return ResearchResponse(
        query_id=result.query_id,
        thread_id=result.thread_id,
        status=ResearchStatus(result.status.value),
        mode=ResearchMode(result.mode.value) if result.mode else None,
        final_report=result.final_report,
        clarification_question=result.clarification_question,
        token_usage=result.token_usage,
        iterations=result.iterations,
        sources=result.sources,
        execution_path=result.execution_path,
    )


@router.post("/run/stream")
async def run_research_stream(
    body: ResearchRequest,
    request: Request,
    use_case: StreamResearchUseCase = Depends(_get_stream_use_case),
) -> StreamingResponse:
    user_id = _user_id(request)
    tracker = get_tracker("research-service")

    # PREVENTION: query must not be blank
    if tracker:
        tracker.prevent("stream-query-non-empty", condition=bool(body.query and body.query.strip()),
                        context={"user_id": user_id, "thread_id": body.thread_id})

    conv = _get_conv_client()

    if body.thread_id and user_id:
        await conv.ensure_thread(body.thread_id, user_id, title=body.query[:60])
        history = await conv.get_history(body.thread_id, limit=20)
    else:
        history = body.history

    job = ResearchJob(
        query_id=str(uuid.uuid4()),
        thread_id=body.thread_id,
        query=body.query,
        user_id=user_id,
        history=history,
        budget_limit=body.budget_limit,
    )

    async def event_generator():
        try:
            async for data in await use_case.execute(job):
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            if tracker:
                tracker.rectify(exc, operation="stream_event_generator",
                                context={"thread_id": body.thread_id, "user_id": user_id})
            import json
            yield f'data: {json.dumps({"type": "error", "message": str(exc)})}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
