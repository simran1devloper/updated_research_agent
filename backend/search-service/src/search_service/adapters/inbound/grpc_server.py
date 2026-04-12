"""gRPC inbound adapter for the Search Service (port 50053)."""
import logging
import grpc
from shared.proto import search_pb2, search_pb2_grpc
from ...container import SearchContainer

logger = logging.getLogger(__name__)


class SearchGrpcServicer(search_pb2_grpc.SearchServiceServicer):
    async def Search(self, request, context):
        use_case = SearchContainer.instance().execute_search_use_case()
        results = await use_case.execute(
            query=request.query,
            sites=list(request.sites),
            limit=request.limit or 5,
            use_tavily=request.use_tavily,
            use_google=request.use_google,
        )
        return search_pb2.SearchResponse(
            results=[
                search_pb2.SearchResult(content=r.content, source=r.source, url=r.url)
                for r in results.items
            ]
        )


async def serve(port: int = 50053) -> None:
    server = grpc.aio.server()
    search_pb2_grpc.add_SearchServiceServicer_to_server(SearchGrpcServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Search gRPC server listening on :%d", port)
    await server.wait_for_termination()
