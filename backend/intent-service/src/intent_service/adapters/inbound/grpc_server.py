"""gRPC inbound adapter for the Intent Service (port 50051)."""
import asyncio
import logging
import grpc
from shared.proto import intent_pb2, intent_pb2_grpc
from ...container import IntentContainer

logger = logging.getLogger(__name__)


class IntentGrpcServicer(intent_pb2_grpc.IntentServiceServicer):
    async def Classify(self, request, context):
        use_case = IntentContainer.instance().classify_intent_use_case()
        history = [{"role": h.role, "content": h.content} for h in request.history]
        result = await use_case.execute(query=request.query, history=history)
        return intent_pb2.ClassifyResponse(
            confidence_score=result.confidence_score,
            is_clear=result.is_clear,
            clarification_question=result.clarification_question,
            category=result.category.value,
        )


async def serve(port: int = 50051) -> None:
    server = grpc.aio.server()
    intent_pb2_grpc.add_IntentServiceServicer_to_server(IntentGrpcServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Intent gRPC server listening on :%d", port)
    await server.wait_for_termination()
