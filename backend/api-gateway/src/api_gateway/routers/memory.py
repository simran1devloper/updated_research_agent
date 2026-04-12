"""Gateway router: memory search endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from shared.models import MemorySearchRequest, MemorySearchResponse

from ..adapters.service_clients import MemoryServiceClient
from ..container import GatewayContainer

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def _get_memory_client() -> MemoryServiceClient:
    return GatewayContainer.instance().memory_client()


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    body: MemorySearchRequest,
    client: MemoryServiceClient = Depends(_get_memory_client),
) -> MemorySearchResponse:
    try:
        data = await client.search(query=body.query, limit=body.limit)
        return MemorySearchResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Memory service unavailable: {exc}")
