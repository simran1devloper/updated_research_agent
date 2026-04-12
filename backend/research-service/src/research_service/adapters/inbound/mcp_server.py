"""
MCP (Model Context Protocol) server for the Research Service.
Exposes `run_research` as a tool so any MCP-compatible AI agent can call it.
Runs on port 8006 (SSE transport).
"""
import uuid
import logging
from mcp.server.fastmcp import FastMCP
from ...container import ResearchContainer
from ...domain.models import ResearchJob

logger = logging.getLogger(__name__)

mcp = FastMCP("research-agent")


@mcp.tool()
async def run_research(query: str, thread_id: str = "", budget_limit: int = 5000) -> dict:
    """
    Run a deep research workflow on the given query.

    Args:
        query: The research question or topic.
        thread_id: Optional conversation thread ID for context continuity.
        budget_limit: Max token budget for the research run.

    Returns:
        dict with keys: query_id, status, final_report, sources, token_usage, iterations.
    """
    use_case = ResearchContainer.instance().run_research_use_case()
    job = ResearchJob(
        query_id=str(uuid.uuid4()),
        thread_id=thread_id or str(uuid.uuid4()),
        query=query,
        budget_limit=budget_limit,
    )
    result = await use_case.execute(job)
    return {
        "query_id": result.query_id,
        "status": result.status.value,
        "final_report": result.final_report,
        "clarification_question": result.clarification_question,
        "sources": result.sources,
        "token_usage": result.token_usage,
        "iterations": result.iterations,
    }


@mcp.tool()
async def search_memory(query: str, limit: int = 5) -> dict:
    """
    Search past research stored in memory for relevant context.

    Args:
        query: The search query.
        limit: Max number of results to return.

    Returns:
        dict with key `contexts` containing a list of relevant text snippets.
    """
    memory_client = ResearchContainer.instance().memory_client()
    contexts = await memory_client.search(query=query, limit=limit)
    return {"contexts": contexts}
