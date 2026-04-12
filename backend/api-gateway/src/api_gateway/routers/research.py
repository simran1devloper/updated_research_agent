"""Gateway router: research endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from shared.models import ResearchRequest, ResearchResponse

from ..adapters.service_clients import ResearchServiceClient
from ..container import GatewayContainer

router = APIRouter(prefix="/api/v1/research", tags=["research"])


def _get_research_client() -> ResearchServiceClient:
    return GatewayContainer.instance().research_client()


def _user_headers(request: Request) -> dict:
    """Build internal identity headers from validated gateway state."""
    return {
        "X-User-ID": getattr(request.state, "user_id", ""),
        "X-User-Email": getattr(request.state, "email", ""),
        "X-User-Role": getattr(request.state, "role", ""),
    }


@router.post("/run", response_model=ResearchResponse)
async def run_research(
    body: ResearchRequest,
    request: Request,
    client: ResearchServiceClient = Depends(_get_research_client),
) -> ResearchResponse:
    try:
        data = await client.run(body.model_dump(), headers=_user_headers(request))
        return ResearchResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research service unavailable: {exc}")


@router.post("/run/stream")
async def run_research_stream(
    body: ResearchRequest,
    request: Request,
    client: ResearchServiceClient = Depends(_get_research_client),
) -> StreamingResponse:
    headers = _user_headers(request)

    async def event_generator():
        try:
            async for line in client.stream(body.model_dump(), headers=headers):
                if line:
                    yield f"{line}\n"
        except Exception as exc:
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
