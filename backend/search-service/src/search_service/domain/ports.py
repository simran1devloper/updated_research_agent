"""Ports for the Search Service domain."""
from abc import ABC, abstractmethod
from .models import SearchQuery, SearchResults, SearchItem


class ISearchProvider(ABC):
    """Outbound port: any search backend (Tavily, Google, DuckDuckGo)."""

    @abstractmethod
    async def search(self, query: str, limit: int) -> SearchResults:
        ...


class ISiteSearchProvider(ABC):
    """Outbound port: site-restricted search (Google CSE)."""

    @abstractmethod
    async def search_site(self, query: str, site: str, limit: int) -> SearchResults:
        ...


class IWebFetcher(ABC):
    """Outbound port: fetch full page content from a URL."""

    @abstractmethod
    async def fetch(self, url: str) -> str | None:
        ...

    @abstractmethod
    async def is_alive(self, url: str) -> bool:
        ...


class ISearchOrchestrator(ABC):
    """Inbound port: coordinate multiple search providers."""

    @abstractmethod
    async def execute(self, query: SearchQuery) -> SearchResults:
        ...
