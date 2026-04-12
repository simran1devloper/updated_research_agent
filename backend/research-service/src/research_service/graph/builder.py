"""
Builds the LangGraph StateGraph for the research workflow.
Wires all nodes together with routing edges.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ResearchState
from .nodes import (
    make_guard_node,
    make_context_node,
    make_intent_node,
    make_clarify_node,
    make_planner_node,
    make_quick_mode_node,
    make_deep_research_node,
    make_gap_analysis_node,
    make_synthesize_node,
    make_formatter_node,
)
from ..domain.ports import (
    IIntentClientPort,
    IMemoryClientPort,
    ISearchClientPort,
    ISynthesisClientPort,
    IConversationClientPort,
)

_MAX_ITERATIONS = 3
_CONFIDENCE_THRESHOLD = 0.8


def build_research_graph(
    intent_port: IIntentClientPort,
    memory_port: IMemoryClientPort,
    search_port: ISearchClientPort,
    synthesis_port: ISynthesisClientPort,
    conversation_port: IConversationClientPort,
):
    """Return a compiled LangGraph with all nodes wired up."""

    graph = StateGraph(ResearchState)

    # Register nodes
    graph.add_node("guard", make_guard_node())
    graph.add_node("context_retrieval", make_context_node(memory_port))
    graph.add_node("intent_orchestrator", make_intent_node(intent_port))
    graph.add_node("clarify_user", make_clarify_node())
    graph.add_node("planner", make_planner_node())
    graph.add_node("quick_mode", make_quick_mode_node(synthesis_port))
    graph.add_node("deep_research", make_deep_research_node(search_port))
    graph.add_node("gap_analysis", make_gap_analysis_node(synthesis_port))
    graph.add_node("synthesize", make_synthesize_node(synthesis_port))
    graph.add_node("formatter", make_formatter_node(memory_port, conversation_port))

    # Entry
    graph.set_entry_point("guard")

    # Linear pre-processing
    graph.add_edge("guard", "context_retrieval")
    graph.add_edge("context_retrieval", "intent_orchestrator")

    # Intent routing
    graph.add_conditional_edges(
        "intent_orchestrator",
        _route_intent,
        {
            "planner": "planner",
            "clarify_user": "clarify_user",
        },
    )
    graph.add_edge("clarify_user", END)

    # Mode routing
    graph.add_conditional_edges(
        "planner",
        _route_mode,
        {
            "quick_mode": "quick_mode",
            "deep_research": "deep_research",
        },
    )

    # Quick path
    graph.add_edge("quick_mode", "formatter")

    # Deep research loop
    graph.add_edge("deep_research", "gap_analysis")
    graph.add_conditional_edges(
        "gap_analysis",
        _route_gap_analysis,
        {
            "synthesize": "synthesize",
            "deep_research": "deep_research",
        },
    )
    graph.add_edge("synthesize", "formatter")
    graph.add_edge("formatter", END)

    return graph.compile(checkpointer=MemorySaver())


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def _route_intent(state: ResearchState) -> str:
    return "planner" if state.get("is_clarified") else "clarify_user"


def _route_mode(state: ResearchState) -> str:
    return "quick_mode" if state.get("mode") == "quick" else "deep_research"


def _route_gap_analysis(state: ResearchState) -> str:
    confidence = state.get("research_confidence_score", 0.0)
    iterations = state.get("iterations", 0)
    if confidence >= _CONFIDENCE_THRESHOLD or iterations >= _MAX_ITERATIONS:
        return "synthesize"
    return "deep_research"
