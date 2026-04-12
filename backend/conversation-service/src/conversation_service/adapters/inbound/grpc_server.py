"""gRPC inbound adapter for the Conversation Service (port 50056)."""
import logging
import grpc
from shared.proto import conversation_pb2, conversation_pb2_grpc
from ...container import ConversationContainer

logger = logging.getLogger(__name__)


class ConversationGrpcServicer(conversation_pb2_grpc.ConversationServiceServicer):
    async def EnsureThread(self, request, context):
        thread = await ConversationContainer.instance().ensure_thread_use_case().execute(
            thread_id=request.thread_id,
            user_id=request.user_id,
            title=request.title,
        )
        return conversation_pb2.ThreadResponse(
            thread_id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            created_at=thread.created_at.isoformat(),
        )

    async def AppendMessage(self, request, context):
        msg = await ConversationContainer.instance().append_message_use_case().execute(
            thread_id=request.thread_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
        )
        return conversation_pb2.MessageResponse(
            message_id=msg.id,
            thread_id=msg.thread_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat(),
        )

    async def GetHistory(self, request, context):
        messages = await ConversationContainer.instance().get_history_use_case().execute(
            thread_id=request.thread_id,
            limit=request.limit or 50,
        )
        return conversation_pb2.GetHistoryResponse(
            messages=[
                conversation_pb2.HistoryMessage(role=m.role, content=m.content)
                for m in messages
            ]
        )


async def serve(port: int = 50056) -> None:
    server = grpc.aio.server()
    conversation_pb2_grpc.add_ConversationServiceServicer_to_server(
        ConversationGrpcServicer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Conversation gRPC server listening on :%d", port)
    await server.wait_for_termination()
