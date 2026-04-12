"""Gateway router: aggregated health check across all services."""
import asyncio
from fastapi import APIRouter
from ..container import GatewayContainer

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/")
async def health_check() -> dict:
    container = GatewayContainer.instance()
    clients = {
        "intent-service": container.intent_client(),
        "memory-service": container.memory_client(),
        "search-service": container.search_client(),
        "synthesis-service": container.synthesis_client(),
        "research-service": container.research_client(),
    }

    async def probe(name: str, client) -> tuple[str, str]:
        try:
            await client.health()
            return name, "ok"
        except Exception:
            return name, "unreachable"

    results = await asyncio.gather(
        *[probe(name, client) for name, client in clients.items()]
    )

    statuses = dict(results)
    overall = "ok" if all(v == "ok" for v in statuses.values()) else "degraded"
    return {"gateway": "ok", "services": statuses, "overall": overall}
