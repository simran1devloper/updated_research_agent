"""LangGraph state definition for the research workflow."""
from typing import TypedDict, Annotated
import operator


class ResearchState(TypedDict):
    # Input
    query: str
    thread_id: str
    query_id: str
    user_id: str
    history: list[dict]
    budget_limit: int

    # Pre-processing
    context: list[str]
    intent: str
    is_clarified: bool
    clarification_question: str
    confidence_score: float

    # Planning
    mode: str

    # Execution
    research_data: Annotated[list[dict], operator.add]
    iterations: int
    gaps: list[str]
    research_confidence_score: float

    # Output
    final_report: str
    token_usage: int
    sources: list[str]

    # Tracing
    execution_path: Annotated[list[str], operator.add]
