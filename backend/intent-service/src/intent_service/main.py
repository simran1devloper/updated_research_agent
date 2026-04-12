"""
Entry point for the Intent Service.
Run with: uvicorn intent_service.main:app --host 0.0.0.0 --port 8001
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))  # reach shared/

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from shared.middleware import add_observability

from .adapters.inbound.http_router import router
from .adapters.inbound.grpc_server import serve as grpc_serve
from .container import IntentContainer

app = FastAPI(
    title="Intent Service",
    description="Classifies user query intent using an LLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

add_observability(app, service_name="intent-service")

@app.on_event("startup")
async def startup() -> None:
    IntentContainer.instance()
    asyncio.ensure_future(grpc_serve())
