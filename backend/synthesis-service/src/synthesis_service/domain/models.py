"""Domain models for the Synthesis Service."""
from dataclasses import dataclass, field


@dataclass
class ResearchItem:
    content: str
    source: str
    url: str


@dataclass
class SynthesisInput:
    query: str
    research_data: list[ResearchItem]
    history: list[dict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class GapAnalysisInput:
    query: str
    research_data: list[ResearchItem]
    iteration: int = 0


@dataclass
class GapAnalysisOutput:
    confidence_score: float
    gaps: list[str]

    def is_sufficient(self, threshold: float = 0.8) -> bool:
        return self.confidence_score >= threshold


@dataclass
class SynthesisOutput:
    report: str
    citations: list[str]
    token_usage: int = 0
