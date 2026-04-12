"""Entry point for the API Gateway. Port: 8000"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from shared.middleware import add_observability

from .routers import research, memory, health, conversations
from .container import GatewayContainer
from .middleware.auth import JWTAuthMiddleware

app = FastAPI(
    title="AI Research Agent — API Gateway",
    description="Single entry point that routes to all microservices.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_credentials=False,  # Bearer token auth — cookies not used, wildcard origin requires False
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JWTAuthMiddleware)

app.include_router(research.router)
app.include_router(memory.router)
app.include_router(health.router)
app.include_router(conversations.router)

add_observability(app, service_name="api-gateway")


@app.on_event("startup")
async def startup() -> None:
    GatewayContainer.instance()


@app.get("/")
async def root() -> dict:
    return {"service": "api-gateway", "docs": "/docs"}
