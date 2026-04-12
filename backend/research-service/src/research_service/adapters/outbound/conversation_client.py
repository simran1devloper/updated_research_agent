"""gRPC client adapter for the Conversation Service."""
import logging
import grpc
from shared.proto import conversation_pb2, conversation_pb2_grpc

logger = logging.getLogger(__name__)


class ConversationServiceClient:
    def __init__(self, grpc_host: str = "conversation-service", grpc_port: int = 50056) -> None:
        self._addr = f"{grpc_host}:{grpc_port}"

    async def ensure_thread(self, thread_id: str, user_id: str, title: str = "") -> None:
        try:
            async with grpc.aio.insecure_channel(self._addr) as ch:
                stub = conversation_pb2_grpc.ConversationServiceStub(ch)
                await stub.EnsureThread(conversation_pb2.EnsureThreadRequest(
                    thread_id=thread_id, user_id=user_id, title=title,
                ))
        except Exception as exc:
            logger.warning("EnsureThread failed: %s", exc)

    async def append_message(self, thread_id: str, role: str, content: str, metadata: str = "") -> None:
        try:
            async with grpc.aio.insecure_channel(self._addr) as ch:
                stub = conversation_pb2_grpc.ConversationServiceStub(ch)
                await stub.AppendMessage(conversation_pb2.AppendMessageRequest(
                    thread_id=thread_id, role=role, content=content, metadata=metadata,
                ))
        except Exception as exc:
            logger.warning("AppendMessage failed: %s", exc)

    async def get_history(self, thread_id: str, limit: int = 20) -> list[dict]:
        try:
            async with grpc.aio.insecure_channel(self._addr) as ch:
                stub = conversation_pb2_grpc.ConversationServiceStub(ch)
                resp = await stub.GetHistory(conversation_pb2.GetHistoryRequest(
                    thread_id=thread_id, limit=limit,
                ))
                return [{"role": m.role, "content": m.content} for m in resp.messages]
        except Exception as exc:
            logger.warning("GetHistory failed: %s", exc)
            return []
