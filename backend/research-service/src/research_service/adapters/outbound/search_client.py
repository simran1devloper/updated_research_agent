"""gRPC client adapter for the Search Service."""
import logging
import grpc
from shared.proto import search_pb2, search_pb2_grpc
from ...domain.ports import ISearchClientPort

logger = logging.getLogger(__name__)


class SearchServiceClient(ISearchClientPort):
    def __init__(self, grpc_host: str = "search-service", grpc_port: int = 50053) -> None:
        self._addr = f"{grpc_host}:{grpc_port}"

    async def search(self, query: str, sites: list[str] | None = None, limit: int = 5) -> list[dict]:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = search_pb2_grpc.SearchServiceStub(channel)
                resp = await stub.Search(search_pb2.SearchRequest(
                    query=query,
                    sites=sites or [],
                    limit=limit,
                    use_tavily=True,
                    use_google=True,
                ))
                return [{"content": r.content, "source": r.source, "url": r.url} for r in resp.results]
        except Exception as exc:
            logger.error("Search gRPC call failed: %s", exc)
            return []
