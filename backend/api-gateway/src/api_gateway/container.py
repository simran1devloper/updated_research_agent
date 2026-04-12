"""DI container for the API Gateway."""
from dependency_injector import containers, providers
from shared.config import ServiceURLs

from .adapters.service_clients import (
    ResearchServiceClient,
    MemoryServiceClient,
    IntentServiceClient,
    SearchServiceClient,
    SynthesisServiceClient,
)


class GatewayContainer(containers.DeclarativeContainer):
    service_urls = providers.Singleton(ServiceURLs)

    research_client = providers.Singleton(
        ResearchServiceClient,
        base_url=service_urls.provided.research_url,
    )

    memory_client = providers.Singleton(
        MemoryServiceClient,
        base_url=service_urls.provided.memory_url,
    )

    intent_client = providers.Singleton(
        IntentServiceClient,
        base_url=service_urls.provided.intent_url,
    )

    search_client = providers.Singleton(
        SearchServiceClient,
        base_url=service_urls.provided.search_url,
    )

    synthesis_client = providers.Singleton(
        SynthesisServiceClient,
        base_url=service_urls.provided.synthesis_url,
    )

    _instance: "GatewayContainer | None" = None

    @classmethod
    def instance(cls) -> "GatewayContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
