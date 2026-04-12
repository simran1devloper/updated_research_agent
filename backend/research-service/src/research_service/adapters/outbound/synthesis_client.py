"""gRPC client adapter for the Synthesis Service."""
import logging
import grpc
from shared.proto import synthesis_pb2, synthesis_pb2_grpc
from ...domain.ports import ISynthesisClientPort

logger = logging.getLogger(__name__)


def _to_pb_items(research_data: list[dict]):
    return [synthesis_pb2.ResearchItem(
        content=r.get("content", ""), source=r.get("source", ""), url=r.get("url", "")
    ) for r in research_data]


def _to_pb_history(history: list[dict]):
    return [synthesis_pb2.HistoryItem(
        role=h.get("role", ""), content=h.get("content", "")
    ) for h in history]


class SynthesisServiceClient(ISynthesisClientPort):
    def __init__(self, grpc_host: str = "synthesis-service", grpc_port: int = 50054) -> None:
        self._addr = f"{grpc_host}:{grpc_port}"

    async def synthesize(self, query: str, research_data: list[dict], history: list[dict], gaps: list[str]) -> dict:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = synthesis_pb2_grpc.SynthesisServiceStub(channel)
                resp = await stub.Synthesize(synthesis_pb2.SynthesisRequest(
                    query=query,
                    research_data=_to_pb_items(research_data),
                    history=_to_pb_history(history),
                    gaps=gaps,
                ))
                return {"report": resp.report, "citations": list(resp.citations), "token_usage": resp.token_usage}
        except Exception as exc:
            logger.error("Synthesis gRPC call failed: %s", exc)
            return {"report": f"Synthesis failed: {exc}", "citations": [], "token_usage": 0}

    async def synthesize_stream(self, query: str, research_data: list[dict], history: list[dict], gaps: list[str]):
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = synthesis_pb2_grpc.SynthesisServiceStub(channel)
                async for chunk in stub.SynthesizeStream(synthesis_pb2.SynthesisRequest(
                    query=query,
                    research_data=_to_pb_items(research_data),
                    history=_to_pb_history(history),
                    gaps=gaps,
                )):
                    yield chunk.chunk
        except Exception as exc:
            logger.error("Synthesis gRPC stream failed: %s", exc)

    async def analyze_gaps(self, query: str, research_data: list[dict], iteration: int) -> dict:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = synthesis_pb2_grpc.SynthesisServiceStub(channel)
                resp = await stub.AnalyzeGaps(synthesis_pb2.GapAnalysisRequest(
                    query=query,
                    research_data=_to_pb_items(research_data),
                    iteration=iteration,
                ))
                return {"confidence_score": resp.confidence_score, "gaps": list(resp.gaps)}
        except Exception as exc:
            logger.warning("Gap analysis gRPC call failed: %s", exc)
            return {"confidence_score": 0.5, "gaps": []}
