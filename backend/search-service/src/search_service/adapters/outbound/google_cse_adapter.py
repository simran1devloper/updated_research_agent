"""Outbound adapter: Google Custom Search Engine (CSE)."""
import logging
import httpx

from ...domain.models import SearchResults, SearchItem
from ...domain.ports import ISiteSearchProvider

logger = logging.getLogger(__name__)

_GOOGLE_API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleCSEAdapter(ISiteSearchProvider):
    def __init__(self, api_key: str, cse_id: str) -> None:
        self._api_key = api_key
        self._cse_id = cse_id

    async def search_site(self, query: str, site: str, limit: int) -> SearchResults:
        if not self._api_key or not self._cse_id:
            return SearchResults()

        full_query = f"site:{site} {query}" if site else query
        params = {
            "key": self._api_key,
            "cx": self._cse_id,
            "q": full_query,
            "num": min(limit, 10),
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(_GOOGLE_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = [
                SearchItem(
                    content=item.get("snippet", ""),
                    source="google_cse",
                    url=item.get("link", ""),
                )
                for item in data.get("items", [])
                if item.get("link")
            ]
            return SearchResults(items=items)
        except Exception as exc:
            logger.warning("Google CSE search failed: %s", exc)
            return SearchResults()
