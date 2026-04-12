"""gRPC client adapter for the Intent Service."""
import logging
import grpc
from shared.proto import intent_pb2, intent_pb2_grpc
from ...domain.ports import IIntentClientPort

logger = logging.getLogger(__name__)


class IntentServiceClient(IIntentClientPort):
    def __init__(self, grpc_host: str = "intent-service", grpc_port: int = 50051) -> None:
        self._addr = f"{grpc_host}:{grpc_port}"

    async def classify(self, query: str, history: list[dict]) -> dict:
        try:
            async with grpc.aio.insecure_channel(self._addr) as channel:
                stub = intent_pb2_grpc.IntentServiceStub(channel)
                pb_history = [
                    intent_pb2.HistoryItem(role=h.get("role", ""), content=h.get("content", ""))
                    for h in history
                ]
                resp = await stub.Classify(intent_pb2.ClassifyRequest(query=query, history=pb_history))
                return {
                    "confidence_score": resp.confidence_score,
                    "is_clear": resp.is_clear,
                    "clarification_question": resp.clarification_question,
                    "category": resp.category,
                }
        except Exception as exc:
            logger.error("Intent gRPC call failed: %s", exc)
            return {"confidence_score": 0.5, "is_clear": False,
                    "clarification_question": "Could you clarify?", "category": "GENERAL"}
