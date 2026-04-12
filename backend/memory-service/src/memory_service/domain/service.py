"""Domain service for memory operations."""
from .models import MemoryRecord, ContextSearchRequest, ContextSearchResult
from .ports import IMemoryRepository, IMemoryService


class MemoryDomainService(IMemoryService):
    def __init__(self, repository: IMemoryRepository) -> None:
        self._repo = repository

    async def store_memory(self, record: MemoryRecord) -> None:
        await self._repo.store(record)

    async def retrieve_context(self, request: ContextSearchRequest) -> ContextSearchResult:
        return await self._repo.search(request)
