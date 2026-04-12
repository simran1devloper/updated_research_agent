"""gRPC inbound adapter for the Auth Service (port 50055)."""
import logging
import grpc
from shared.proto import auth_pb2, auth_pb2_grpc
from ...container import AuthContainer

logger = logging.getLogger(__name__)


class AuthGrpcServicer(auth_pb2_grpc.AuthServiceServicer):
    async def ValidateToken(self, request, context):
        claims = AuthContainer.instance().validate_token_use_case().execute(request.token)
        return auth_pb2.ValidateTokenResponse(
            valid=claims.valid,
            user_id=claims.user_id,
            email=claims.email,
            role=claims.role,
            error=claims.error,
        )

    async def GetUser(self, request, context):
        user = await AuthContainer.instance().get_user_use_case().execute(request.user_id)
        if not user:
            await context.abort(grpc.StatusCode.NOT_FOUND, "User not found")
        return auth_pb2.UserResponse(
            user_id=user.id,
            email=user.email,
            username=user.username,
            role=user.role.value,
            is_active=user.is_active,
        )


async def serve(port: int = 50055) -> None:
    server = grpc.aio.server()
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthGrpcServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Auth gRPC server listening on :%d", port)
    await server.wait_for_termination()
