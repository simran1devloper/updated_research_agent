"""Entry point for the Auth Service. Port: 8007 (REST) | 50055 (gRPC)"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from shared.middleware import add_observability

from .adapters.inbound.http_router import router
from .adapters.inbound.grpc_server import serve as grpc_serve
from .container import AuthContainer
from .db.session import init_db

app = FastAPI(title="Auth Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

add_observability(app, service_name="auth-service")


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    AuthContainer.instance()
    asyncio.ensure_future(grpc_serve())
