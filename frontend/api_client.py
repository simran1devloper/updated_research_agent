"""
HTTP client used by the Streamlit frontend to talk to the API Gateway.
Frontend never calls microservices directly.
"""
import httpx
from config import API_GATEWAY_URL


class GatewayClient:
    def __init__(self, base_url: str = API_GATEWAY_URL) -> None:
        self._base = base_url.rstrip("/")

    async def run_research(
        self,
        query: str,
        thread_id: str,
        history: list[dict],
        budget_limit: int = 5000,
    ) -> dict:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{self._base}/api/v1/research/run",
                json={
                    "query": query,
                    "thread_id": thread_id,
                    "history": history,
                    "budget_limit": budget_limit,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def run_research_sync(
        self,
        query: str,
        thread_id: str,
        history: list[dict],
        budget_limit: int = 5000,
    ) -> dict:
        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{self._base}/api/v1/research/run",
                json={
                    "query": query,
                    "thread_id": thread_id,
                    "history": history,
                    "budget_limit": budget_limit,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def health_sync(self) -> dict:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self._base}/api/v1/health/")
                return resp.json()
        except Exception as exc:
            return {"overall": "unreachable", "error": str(exc)}

    def search_memory_sync(self, query: str, limit: int = 5) -> list[str]:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    f"{self._base}/api/v1/memory/search",
                    json={"query": query, "limit": limit},
                )
                resp.raise_for_status()
                return resp.json().get("contexts", [])
        except Exception:
            return []
