"""
Domain models for the Intent Service.
Pure Python dataclasses — no framework dependencies.
"""
from dataclasses import dataclass, field
from enum import Enum


class QueryCategory(str, Enum):
    BUG = "BUG"
    ARCHITECTURE = "ARCHITECTURE"
    CONCEPT = "CONCEPT"
    COMPARISON = "COMPARISON"
    RESEARCH = "RESEARCH"
    GENERAL = "GENERAL"
    NON_TECHNICAL = "NON_TECHNICAL"


@dataclass
class IntentClassification:
    """Result of classifying a user query's intent."""
    confidence_score: float
    is_clear: bool
    category: QueryCategory
    clarification_question: str = ""

    def needs_clarification(self) -> bool:
        return not self.is_clear or self.confidence_score < 0.8


@dataclass
class ClassificationRequest:
    """Input to the domain service."""
    query: str
    history: list[dict] = field(default_factory=list)
