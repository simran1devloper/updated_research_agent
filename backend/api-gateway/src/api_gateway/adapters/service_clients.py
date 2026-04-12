"""
HTTP clients used by the gateway to call downstream microservices.
The gateway never directly touches domain logic — it only proxies.
"""
import logging
import httpx

logger = logging.getLogger(__name__)


class ResearchServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def run(self, payload: dict, headers: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{self._base_url}/research/run", json=payload, headers=headers or {})
            resp.raise_for_status()
            return resp.json()

    async def stream(self, payload: dict, headers: dict | None = None):
        """Yields raw SSE lines from the research service."""
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{self._base_url}/research/run/stream", json=payload, headers=headers or {}) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    yield line

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self._base_url}/research/health")
            return resp.json()


class MemoryServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def search(self, query: str, limit: int = 5) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base_url}/memory/search",
                json={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self._base_url}/memory/health")
            return resp.json()


class IntentServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self._base_url}/intent/health")
            return resp.json()


class SearchServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self._base_url}/search/health")
            return resp.json()


class SynthesisServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{self._base_url}/synthesis/health")
            return resp.json()
