"""DI container for the Memory Service."""
from dependency_injector import containers, providers
from shared.config import QdrantSettings

from .adapters.outbound.qdrant_adapter import QdrantMemoryAdapter
from .domain.service import MemoryDomainService
from .application.use_cases import StoreMemoryUseCase, RetrieveContextUseCase


class MemoryContainer(containers.DeclarativeContainer):
    config = providers.Singleton(QdrantSettings)

    qdrant_adapter = providers.Singleton(
        QdrantMemoryAdapter,
        path=config.provided.path,
        collection=config.provided.collection,
    )

    memory_domain_service = providers.Singleton(
        MemoryDomainService,
        repository=qdrant_adapter,
    )

    store_memory_use_case = providers.Factory(
        StoreMemoryUseCase,
        service=memory_domain_service,
    )

    retrieve_context_use_case = providers.Factory(
        RetrieveContextUseCase,
        service=memory_domain_service,
    )

    _instance: "MemoryContainer | None" = None

    @classmethod
    def instance(cls) -> "MemoryContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
