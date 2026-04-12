"""Application use-cases for the Synthesis Service."""
from collections.abc import AsyncIterator
from ..domain.models import (
    SynthesisInput, SynthesisOutput,
    GapAnalysisInput, GapAnalysisOutput,
    ResearchItem,
)
from ..domain.ports import ISynthesisService
from ..domain.service import SynthesisDomainService


class SynthesizeReportUseCase:
    def __init__(self, service: ISynthesisService) -> None:
        self._service = service

    async def execute(
        self,
        query: str,
        research_data: list[dict],
        history: list[dict] | None = None,
        gaps: list[str] | None = None,
    ) -> SynthesisOutput:
        items = [ResearchItem(**d) for d in research_data]
        input_ = SynthesisInput(
            query=query,
            research_data=items,
            history=history or [],
            gaps=gaps or [],
        )
        return await self._service.synthesize(input_)


class SynthesizeStreamUseCase:
    def __init__(self, service: SynthesisDomainService) -> None:
        self._service = service

    async def execute(
        self,
        query: str,
        research_data: list[dict],
        history: list[dict] | None = None,
        gaps: list[str] | None = None,
    ) -> AsyncIterator[str]:
        items = [ResearchItem(**d) for d in research_data]
        input_ = SynthesisInput(
            query=query,
            research_data=items,
            history=history or [],
            gaps=gaps or [],
        )
        async for chunk in self._service.synthesize_stream(input_):
            yield chunk


class AnalyzeGapsUseCase:
    def __init__(self, service: ISynthesisService) -> None:
        self._service = service

    async def execute(
        self,
        query: str,
        research_data: list[dict],
        iteration: int = 0,
    ) -> GapAnalysisOutput:
        items = [ResearchItem(**d) for d in research_data]
        input_ = GapAnalysisInput(query=query, research_data=items, iteration=iteration)
        return await self._service.analyze_gaps(input_)
