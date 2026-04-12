"""Inbound HTTP adapter for the Synthesis Service."""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shared.models import SynthesisRequest, SynthesisResponse, HealthResponse

from ...application.use_cases import SynthesizeReportUseCase, AnalyzeGapsUseCase, SynthesizeStreamUseCase
from ...container import SynthesisContainer

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


class GapAnalysisRequest(BaseModel):
    query: str
    research_data: list[dict]
    iteration: int = 0


class GapAnalysisResponse(BaseModel):
    confidence_score: float
    gaps: list[str]


def _get_synth_use_case() -> SynthesizeReportUseCase:
    return SynthesisContainer.instance().synthesize_report_use_case()


def _get_stream_use_case() -> SynthesizeStreamUseCase:
    return SynthesisContainer.instance().synthesize_stream_use_case()


def _get_gap_use_case() -> AnalyzeGapsUseCase:
    return SynthesisContainer.instance().analyze_gaps_use_case()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="synthesis-service")


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize(
    body: SynthesisRequest,
    use_case: SynthesizeReportUseCase = Depends(_get_synth_use_case),
) -> SynthesisResponse:
    result = await use_case.execute(
        query=body.query,
        research_data=[r.model_dump() for r in body.research_data],
        history=body.history,
        gaps=body.gaps,
    )
    return SynthesisResponse(
        report=result.report,
        citations=result.citations,
        token_usage=result.token_usage,
    )


@router.post("/synthesize/stream")
async def synthesize_stream(
    body: SynthesisRequest,
    use_case: SynthesizeStreamUseCase = Depends(_get_stream_use_case),
) -> StreamingResponse:
    async def event_generator():
        async for chunk in use_case.execute(
            query=body.query,
            research_data=[r.model_dump() for r in body.research_data],
            history=body.history,
            gaps=body.gaps,
        ):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/gaps", response_model=GapAnalysisResponse)
async def analyze_gaps(
    body: GapAnalysisRequest,
    use_case: AnalyzeGapsUseCase = Depends(_get_gap_use_case),
) -> GapAnalysisResponse:
    result = await use_case.execute(
        query=body.query,
        research_data=body.research_data,
        iteration=body.iteration,
    )
    return GapAnalysisResponse(
        confidence_score=result.confidence_score,
        gaps=result.gaps,
    )
