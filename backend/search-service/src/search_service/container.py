"""DI container for the Search Service."""
from dependency_injector import containers, providers
from shared.config import SearchSettings

from .adapters.outbound.tavily_adapter import TavilySearchAdapter
from .adapters.outbound.google_cse_adapter import GoogleCSEAdapter
from .adapters.outbound.duckduckgo_adapter import DuckDuckGoAdapter
from .adapters.outbound.web_fetcher_adapter import WebFetcherAdapter
from .domain.service import SearchDomainService
from .application.use_cases import ExecuteSearchUseCase


class SearchContainer(containers.DeclarativeContainer):
    config = providers.Singleton(SearchSettings)

    tavily_adapter = providers.Singleton(
        TavilySearchAdapter,
        api_key=config.provided.tavily_api_key,
    )

    google_adapter = providers.Singleton(
        GoogleCSEAdapter,
        api_key=config.provided.google_api_key,
        cse_id=config.provided.google_cse_id,
    )

    duckduckgo_adapter = providers.Singleton(DuckDuckGoAdapter)

    web_fetcher_adapter = providers.Singleton(WebFetcherAdapter)

    search_domain_service = providers.Singleton(
        SearchDomainService,
        primary_provider=tavily_adapter,
        fallback_provider=duckduckgo_adapter,
        site_provider=google_adapter,
        web_fetcher=web_fetcher_adapter,
    )

    execute_search_use_case = providers.Factory(
        ExecuteSearchUseCase,
        orchestrator=search_domain_service,
    )

    _instance: "SearchContainer | None" = None

    @classmethod
    def instance(cls) -> "SearchContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
