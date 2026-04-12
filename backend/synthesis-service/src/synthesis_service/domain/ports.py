"""Ports for the Synthesis Service domain."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from .models import SynthesisInput, SynthesisOutput, GapAnalysisInput, GapAnalysisOutput


class ILLMPort(ABC):
    @abstractmethod
    async def synthesize(self, prompt: str) -> tuple[str, int]:
        """Returns (report_text, token_count)."""
        ...

    @abstractmethod
    async def synthesize_stream(self, prompt: str) -> AsyncIterator[str]:  # type: ignore[override]
        """Yields text chunks as they arrive."""
        yield  # pragma: no cover

    @abstractmethod
    async def analyze_gaps(self, prompt: str) -> dict:
        """Returns raw dict: {confidence_score, gaps}."""
        ...


class ISynthesisService(ABC):
    @abstractmethod
    async def synthesize(self, input_: SynthesisInput) -> SynthesisOutput:
        ...

    @abstractmethod
    async def synthesize_stream(self, input_: SynthesisInput) -> AsyncIterator[str]:  # type: ignore[override]
        yield  # pragma: no cover

    @abstractmethod
    async def analyze_gaps(self, input_: GapAnalysisInput) -> GapAnalysisOutput:
        ...
