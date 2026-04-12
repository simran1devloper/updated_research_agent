"""
Search domain service.
Orchestrates multiple search providers, deduplicates results,
and enriches thin snippets with full-page content.
"""
import asyncio
import logging

from .models import SearchQuery, SearchResults, SearchItem
from .ports import ISearchProvider, ISiteSearchProvider, IWebFetcher, ISearchOrchestrator

logger = logging.getLogger(__name__)

_MIN_CONTENT_LEN = 200  # snippets shorter than this get full-page fetch


class SearchDomainService(ISearchOrchestrator):
    def __init__(
        self,
        primary_provider: ISearchProvider,       # Tavily
        fallback_provider: ISearchProvider,      # DuckDuckGo
        site_provider: ISiteSearchProvider,      # Google CSE
        web_fetcher: IWebFetcher,
    ) -> None:
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._site = site_provider
        self._fetcher = web_fetcher

    async def execute(self, query: SearchQuery) -> SearchResults:
        tasks = []

        if query.use_tavily:
            tasks.append(self._primary.search(query.query, query.limit))

        if query.sites:
            for site in query.sites[:3]:
                tasks.append(self._site.search_site(query.query, site, 3))
        elif query.use_google:
            tasks.append(self._site.search_site(query.query, "", query.limit))

        if not tasks:
            tasks.append(self._fallback.search(query.query, query.limit))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        combined = SearchResults()
        for r in results_list:
            if isinstance(r, SearchResults):
                combined.extend(r)
            else:
                logger.warning("A search task failed: %s", r)

        # Fallback if primary search returned nothing
        if not combined.items:
            fallback = await self._fallback.search(query.query, query.limit)
            combined.extend(fallback)

        deduped = combined.deduplicated()

        # Enrich thin snippets
        enriched = await self._enrich(deduped)
        return enriched

    async def _enrich(self, results: SearchResults) -> SearchResults:
        enriched_items: list[SearchItem] = []
        for item in results.items:
            if len(item.content) < _MIN_CONTENT_LEN:
                if await self._fetcher.is_alive(item.url):
                    full = await self._fetcher.fetch(item.url)
                    if full:
                        item = SearchItem(
                            content=full[:3000],
                            source=item.source,
                            url=item.url,
                        )
            enriched_items.append(item)
        return SearchResults(items=enriched_items)
