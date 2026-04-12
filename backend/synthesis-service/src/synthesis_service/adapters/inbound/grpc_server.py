"""gRPC inbound adapter for the Synthesis Service (port 50054)."""
import logging
import grpc
from shared.proto import synthesis_pb2, synthesis_pb2_grpc
from ...container import SynthesisContainer

logger = logging.getLogger(__name__)


def _to_items(pb_items) -> list[dict]:
    return [{"content": r.content, "source": r.source, "url": r.url} for r in pb_items]


def _to_history(pb_history) -> list[dict]:
    return [{"role": h.role, "content": h.content} for h in pb_history]


class SynthesisGrpcServicer(synthesis_pb2_grpc.SynthesisServiceServicer):
    async def Synthesize(self, request, context):
        use_case = SynthesisContainer.instance().synthesize_report_use_case()
        result = await use_case.execute(
            query=request.query,
            research_data=_to_items(request.research_data),
            history=_to_history(request.history),
            gaps=list(request.gaps),
        )
        return synthesis_pb2.SynthesisResponse(
            report=result.report,
            citations=result.citations,
            token_usage=result.token_usage,
        )

    async def AnalyzeGaps(self, request, context):
        use_case = SynthesisContainer.instance().analyze_gaps_use_case()
        result = await use_case.execute(
            query=request.query,
            research_data=_to_items(request.research_data),
            iteration=request.iteration,
        )
        return synthesis_pb2.GapAnalysisResponse(
            confidence_score=result.confidence_score,
            gaps=result.gaps,
        )

    async def SynthesizeStream(self, request, context):
        use_case = SynthesisContainer.instance().synthesize_stream_use_case()
        async for chunk in use_case.execute(
            query=request.query,
            research_data=_to_items(request.research_data),
            history=_to_history(request.history),
            gaps=list(request.gaps),
        ):
            yield synthesis_pb2.TokenChunk(chunk=chunk)


async def serve(port: int = 50054) -> None:
    server = grpc.aio.server()
    synthesis_pb2_grpc.add_SynthesisServiceServicer_to_server(SynthesisGrpcServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Synthesis gRPC server listening on :%d", port)
    await server.wait_for_termination()
