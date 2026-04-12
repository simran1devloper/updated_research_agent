"""Domain models for the Memory Service."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryRecord:
    query_id: str
    query: str
    response: str
    user_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ContextSearchRequest:
    query: str
    limit: int = 5
    user_id: str = ""


@dataclass
class ContextSearchResult:
    contexts: list[str]
