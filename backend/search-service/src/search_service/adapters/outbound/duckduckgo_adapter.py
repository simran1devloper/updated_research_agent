"""Outbound adapter: DuckDuckGo (free fallback search)."""
import logging
from duckduckgo_search import DDGS

from ...domain.models import SearchResults, SearchItem
from ...domain.ports import ISearchProvider

logger = logging.getLogger(__name__)


class DuckDuckGoAdapter(ISearchProvider):
    async def search(self, query: str, limit: int) -> SearchResults:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=limit))
            items = [
                SearchItem(
                    content=r.get("body", ""),
                    source="duckduckgo",
                    url=r.get("href", ""),
                )
                for r in raw
                if r.get("href")
            ]
            return SearchResults(items=items)
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return SearchResults()
