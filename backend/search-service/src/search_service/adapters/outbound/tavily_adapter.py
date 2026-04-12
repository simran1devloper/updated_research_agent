"""Outbound adapter: Tavily search API."""
import logging
from tavily import AsyncTavilyClient

from ...domain.models import SearchResults, SearchItem
from ...domain.ports import ISearchProvider

logger = logging.getLogger(__name__)


class TavilySearchAdapter(ISearchProvider):
    def __init__(self, api_key: str) -> None:
        self._client = AsyncTavilyClient(api_key=api_key)

    async def search(self, query: str, limit: int) -> SearchResults:
        if not query:
            return SearchResults()
        try:
            resp = await self._client.search(
                query=query,
                max_results=limit,
                search_depth="advanced",
                include_raw_content=False,
            )
            items = [
                SearchItem(
                    content=r.get("content", ""),
                    source="tavily",
                    url=r.get("url", ""),
                )
                for r in resp.get("results", [])
                if r.get("url")
            ]
            return SearchResults(items=items)
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return SearchResults()
