"""gRPC client adapter for the Memory Service."""
import logging
import grpc
from shared.proto import memory_pb2, memory_pb2_grpc
from ...domain.ports import IMemoryClientPort

logger = logging.getLogger(__name__)


class MemoryServiceClient(IMemoryClientPort):
    def __init__(self, grpc_host: str = "memory-service", grpc_port: int = 50052) -> None:
        self._addr = f"{grpc_host}:{grpc_port}"

    async def search(self, query: str, limit: int = 5, user_id: str = "") -> list[str]:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = memory_pb2_grpc.MemoryServiceStub(channel)
                resp = await stub.Search(memory_pb2.MemorySearchRequest(
                    query=query, limit=limit, user_id=user_id
                ))
                return list(resp.contexts)
        except Exception as exc:
            logger.warning("Memory gRPC search failed: %s", exc)
            return []

    async def store(self, query_id: str, query: str, response: str, user_id: str = "") -> None:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = memory_pb2_grpc.MemoryServiceStub(channel)
                await stub.Store(memory_pb2.MemoryStoreRequest(
                    query_id=query_id, query=query, response=response, user_id=user_id
                ))
        except Exception as exc:
            logger.warning("Memory gRPC store failed: %s", exc)
