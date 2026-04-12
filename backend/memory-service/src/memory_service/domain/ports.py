"""Ports (interfaces) for the Memory Service domain."""
from abc import ABC, abstractmethod
from .models import MemoryRecord, ContextSearchRequest, ContextSearchResult


class IMemoryRepository(ABC):
    """Outbound port: persistent vector store for memories."""

    @abstractmethod
    async def store(self, record: MemoryRecord) -> None:
        ...

    @abstractmethod
    async def search(self, request: ContextSearchRequest) -> ContextSearchResult:
        ...


class IMemoryService(ABC):
    """Inbound port: what the application exposes to callers."""

    @abstractmethod
    async def store_memory(self, record: MemoryRecord) -> None:
        ...

    @abstractmethod
    async def retrieve_context(self, request: ContextSearchRequest) -> ContextSearchResult:
        ...
