from typing import TypedDict, List, Annotated, Optional
import operator
from pydantic import BaseModel, Field

class IntentOutput(BaseModel):
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    is_clear: bool = Field(description="Whether the query is clear enough to skip clarification")
    clarification_question: str = Field(description="Question to ask the user if is_clear is False")
    category: str = Field(description="The category of the query (e.g., RESEARCH, BUG, ARCHITECTURE)")

class GapAnalysisOutput(BaseModel):
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    gaps: List[str] = Field(description="List of research gaps or missing information")

class AgentState(TypedDict):
    query: str
    history: Annotated[list, operator.add]
    context: list
    intent: str
    is_clarified: bool
    clarification_question: str  # LLM-generated question when query is ambiguous
    mode: str
    confidence_score: float
    research_confidence_score: float
    research_data: Annotated[list, operator.add]
    final_report: str
    token_usage: int
    budget_limit: int
    gaps: list
    iterations: int
    streaming_chunk: str  # For real-time token streaming
    query_id: str  # Unique ID for streaming buffer