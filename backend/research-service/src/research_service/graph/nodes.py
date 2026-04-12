"""
LangGraph graph nodes for the research workflow.
"""
import logging
import uuid

from ..domain.ports import (
    IIntentClientPort,
    IMemoryClientPort,
    ISearchClientPort,
    ISynthesisClientPort,
    IConversationClientPort,
)
from .state import ResearchState

logger = logging.getLogger(__name__)


def make_guard_node():
    async def guard(state: ResearchState) -> dict:
        return {
            "query_id": state.get("query_id") or str(uuid.uuid4()),
            "iterations": 0,
            "research_data": [],
            "execution_path": ["guard"],
            "token_usage": 0,
        }
    return guard


def make_context_node(memory_port: IMemoryClientPort):
    async def context_retrieval(state: ResearchState) -> dict:
        contexts = await memory_port.search(
            state["query"], limit=5, user_id=state.get("user_id", "")
        )
        return {"context": contexts, "execution_path": ["context_retrieval"]}
    return context_retrieval


def make_intent_node(intent_port: IIntentClientPort):
    async def intent_orchestrator(state: ResearchState) -> dict:
        result = await intent_port.classify(
            query=state["query"],
            history=state.get("history", []),
        )
        return {
            "intent": result.get("category", "GENERAL"),
            "is_clarified": result.get("is_clear", False),
            "clarification_question": result.get("clarification_question", ""),
            "confidence_score": result.get("confidence_score", 0.0),
            "execution_path": ["intent_orchestrator"],
        }
    return intent_orchestrator


def make_clarify_node():
    async def clarify_user(state: ResearchState) -> dict:
        return {"execution_path": ["clarify_user"]}
    return clarify_user


def make_planner_node():
    async def planner(state: ResearchState) -> dict:
        deep_categories = {"ARCHITECTURE", "COMPARISON", "RESEARCH"}
        mode = "deep" if state.get("intent") in deep_categories else "quick"
        return {"mode": mode, "execution_path": ["planner"]}
    return planner


def make_quick_mode_node(synthesis_port: ISynthesisClientPort):
    async def quick_mode(state: ResearchState) -> dict:
        research_data = [
            {"content": ctx, "source": "memory", "url": ""}
            for ctx in state.get("context", [])
        ] or [{"content": state["query"], "source": "direct", "url": ""}]
        result = await synthesis_port.synthesize(
            query=state["query"],
            research_data=research_data,
            history=state.get("history", []),
            gaps=[],
        )
        return {
            "final_report": result.get("report", ""),
            "sources": result.get("citations", []),
            "token_usage": result.get("token_usage", 0),
            "execution_path": ["quick_mode"],
        }
    return quick_mode


def make_deep_research_node(search_port: ISearchClientPort):
    async def deep_research(state: ResearchState) -> dict:
        query = state["query"]
        gaps = state.get("gaps", [])
        search_queries = [query] + [f"{query} {gap}" for gap in gaps[:2]]
        all_results: list[dict] = []
        for sq in search_queries:
            results = await search_port.search(query=sq, limit=5)
            all_results.extend(results)
        return {
            "research_data": all_results,
            "iterations": state.get("iterations", 0) + 1,
            "execution_path": ["deep_research"],
        }
    return deep_research


def make_gap_analysis_node(synthesis_port: ISynthesisClientPort):
    async def gap_analysis(state: ResearchState) -> dict:
        result = await synthesis_port.analyze_gaps(
            query=state["query"],
            research_data=state.get("research_data", []),
            iteration=state.get("iterations", 0),
        )
        return {
            "research_confidence_score": result.get("confidence_score", 0.5),
            "gaps": result.get("gaps", []),
            "execution_path": ["gap_analysis"],
        }
    return gap_analysis


def make_synthesize_node(synthesis_port: ISynthesisClientPort):
    async def synthesize(state: ResearchState) -> dict:
        result = await synthesis_port.synthesize(
            query=state["query"],
            research_data=state.get("research_data", []),
            history=state.get("history", []),
            gaps=state.get("gaps", []),
        )
        return {
            "final_report": result.get("report", ""),
            "sources": result.get("citations", []),
            "token_usage": result.get("token_usage", 0),
            "execution_path": ["synthesize"],
        }
    return synthesize


def make_formatter_node(memory_port: IMemoryClientPort, conversation_port: IConversationClientPort):
    async def formatter(state: ResearchState) -> dict:
        report = state.get("final_report", "")
        user_id = state.get("user_id", "")
        thread_id = state.get("thread_id", "")
        query = state["query"]

        if report and state.get("query_id"):
            # Store in vector memory (scoped to user)
            await memory_port.store(
                query_id=state["query_id"],
                query=query,
                response=report[:500],
                user_id=user_id,
            )
            # Persist messages to conversation history
            if thread_id:
                await conversation_port.append_message(thread_id, "user", query)
                await conversation_port.append_message(thread_id, "assistant", report)

        return {"execution_path": ["formatter"]}
    return formatter
