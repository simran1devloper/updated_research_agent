"""gRPC client for the Auth Service — used by gateway middleware."""
import os
import grpc
from shared.proto import auth_pb2, auth_pb2_grpc


class AuthServiceClient:
    def __init__(
        self,
        grpc_host: str = "auth-service",
        grpc_port: int = 50055,
    ) -> None:
        addr = f"{grpc_host}:{grpc_port}"
        self._channel = grpc.aio.insecure_channel(addr)
        self._stub = auth_pb2_grpc.AuthServiceStub(self._channel)

    async def validate_token(self, token: str) -> auth_pb2.ValidateTokenResponse:
        return await self._stub.ValidateToken(auth_pb2.ValidateTokenRequest(token=token))
