"""gRPC inbound adapter for the Memory Service (port 50052)."""
import logging
import grpc
from shared.proto import memory_pb2, memory_pb2_grpc
from ...container import MemoryContainer

logger = logging.getLogger(__name__)


class MemoryGrpcServicer(memory_pb2_grpc.MemoryServiceServicer):
    async def Search(self, request, context):
        use_case = MemoryContainer.instance().retrieve_context_use_case()
        result = await use_case.execute(
            query=request.query, limit=request.limit or 5, user_id=request.user_id
        )
        return memory_pb2.MemorySearchResponse(contexts=result.contexts)

    async def Store(self, request, context):
        use_case = MemoryContainer.instance().store_memory_use_case()
        await use_case.execute(
            query_id=request.query_id,
            query=request.query,
            response=request.response,
            user_id=request.user_id,
        )
        return memory_pb2.MemoryStoreResponse(ok=True)


async def serve(port: int = 50052) -> None:
    server = grpc.aio.server()
    memory_pb2_grpc.add_MemoryServiceServicer_to_server(MemoryGrpcServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Memory gRPC server listening on :%d", port)
    await server.wait_for_termination()
