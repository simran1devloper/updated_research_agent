"""
Shared Pydantic DTOs used as contracts between microservices.
These are the API-level data transfer objects, NOT domain models.
"""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class QueryCategory(str, Enum):
    BUG = "BUG"
    ARCHITECTURE = "ARCHITECTURE"
    CONCEPT = "CONCEPT"
    COMPARISON = "COMPARISON"
    RESEARCH = "RESEARCH"
    GENERAL = "GENERAL"
    NON_TECHNICAL = "NON_TECHNICAL"


class ResearchMode(str, Enum):
    QUICK = "quick"
    DEEP = "deep"


# ---------------------------------------------------------------------------
# Intent Service DTOs
# ---------------------------------------------------------------------------

class IntentRequest(BaseModel):
    query: str
    history: list[dict[str, str]] = Field(default_factory=list)


class IntentResponse(BaseModel):
    confidence_score: float
    is_clear: bool
    clarification_question: str = ""
    category: QueryCategory


# ---------------------------------------------------------------------------
# Memory Service DTOs
# ---------------------------------------------------------------------------

class MemoryStoreRequest(BaseModel):
    query_id: str
    query: str
    response: str


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5


class MemorySearchResponse(BaseModel):
    contexts: list[str]


# ---------------------------------------------------------------------------
# Search Service DTOs
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    sites: list[str] = Field(default_factory=list)
    limit: int = 5
    use_tavily: bool = True
    use_google: bool = True


class SearchResult(BaseModel):
    content: str
    source: str
    url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


# ---------------------------------------------------------------------------
# Synthesis Service DTOs
# ---------------------------------------------------------------------------

class SynthesisRequest(BaseModel):
    query: str
    research_data: list[SearchResult]
    history: list[dict[str, str]] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class SynthesisResponse(BaseModel):
    report: str
    citations: list[str]
    token_usage: int = 0


# ---------------------------------------------------------------------------
# Research Service DTOs  (orchestrates everything)
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str
    thread_id: str
    history: list[dict[str, str]] = Field(default_factory=list)
    budget_limit: int = 5000


class ResearchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CLARIFYING = "clarifying"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchResponse(BaseModel):
    query_id: str
    thread_id: str
    status: ResearchStatus
    mode: ResearchMode | None = None
    final_report: str = ""
    clarification_question: str = ""
    token_usage: int = 0
    iterations: int = 0
    sources: list[str] = Field(default_factory=list)
    execution_path: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Gateway / health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    service: str
    status: str = "ok"
