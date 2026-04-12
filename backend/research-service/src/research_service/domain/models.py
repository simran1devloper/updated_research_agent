"""Domain models for the Research Service orchestrator."""
from dataclasses import dataclass, field
from enum import Enum


class ResearchMode(str, Enum):
    QUICK = "quick"
    DEEP = "deep"


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CLARIFYING = "clarifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchJob:
    query_id: str
    thread_id: str
    query: str
    user_id: str = ""
    history: list[dict] = field(default_factory=list)
    budget_limit: int = 5000


@dataclass
class ResearchResult:
    query_id: str
    thread_id: str
    status: ResearchStatus
    mode: ResearchMode | None = None
    final_report: str = ""
    clarification_question: str = ""
    token_usage: int = 0
    iterations: int = 0
    sources: list[str] = field(default_factory=list)
    execution_path: list[str] = field(default_factory=list)
