"""Application layer use-cases for the Memory Service."""
from ..domain.models import MemoryRecord, ContextSearchRequest, ContextSearchResult
from ..domain.ports import IMemoryService


class StoreMemoryUseCase:
    def __init__(self, service: IMemoryService) -> None:
        self._service = service

    async def execute(self, query_id: str, query: str, response: str, user_id: str = "") -> None:
        record = MemoryRecord(query_id=query_id, query=query, response=response, user_id=user_id)
        await self._service.store_memory(record)


class RetrieveContextUseCase:
    def __init__(self, service: IMemoryService) -> None:
        self._service = service

    async def execute(self, query: str, limit: int = 5, user_id: str = "") -> ContextSearchResult:
        request = ContextSearchRequest(query=query, limit=limit, user_id=user_id)
        return await self._service.retrieve_context(request)
