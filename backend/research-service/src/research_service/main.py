"""Entry point for the Research Service. Port: 8005 (REST) | 8006 (MCP/SSE)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from shared.middleware import add_observability

from .adapters.inbound.http_router import router
from .adapters.inbound.mcp_server import mcp
from .container import ResearchContainer

app = FastAPI(title="Research Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

# Mount MCP SSE transport at /mcp — agents connect to http://research-service:8005/mcp/sse
app.mount("/mcp", mcp.sse_app())

add_observability(app, service_name="research-service")

@app.on_event("startup")
async def startup() -> None:
    ResearchContainer.instance()
