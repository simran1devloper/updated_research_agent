"""Inbound HTTP adapter for the Memory Service."""
from fastapi import APIRouter, Depends
from shared.models import (
    MemoryStoreRequest, MemorySearchRequest, MemorySearchResponse, HealthResponse
)
from ...application.use_cases import StoreMemoryUseCase, RetrieveContextUseCase
from ...container import MemoryContainer

router = APIRouter(prefix="/memory", tags=["memory"])


def _get_store_use_case() -> StoreMemoryUseCase:
    return MemoryContainer.instance().store_memory_use_case()


def _get_retrieve_use_case() -> RetrieveContextUseCase:
    return MemoryContainer.instance().retrieve_context_use_case()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="memory-service")


@router.post("/store")
async def store_memory(
    body: MemoryStoreRequest,
    use_case: StoreMemoryUseCase = Depends(_get_store_use_case),
) -> dict:
    await use_case.execute(
        query_id=body.query_id,
        query=body.query,
        response=body.response,
    )
    return {"status": "stored"}


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    body: MemorySearchRequest,
    use_case: RetrieveContextUseCase = Depends(_get_retrieve_use_case),
) -> MemorySearchResponse:
    result = await use_case.execute(query=body.query, limit=body.limit)
    return MemorySearchResponse(contexts=result.contexts)
