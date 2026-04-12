"""Gateway router: conversation thread and message endpoints."""
import httpx
import os
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

_CONV_URL = os.getenv("SERVICE_CONVERSATION_URL", "http://conversation-service:8008")


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", "")
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.get("/threads")
async def list_threads(request: Request):
    user_id = _user_id(request)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_CONV_URL}/users/{user_id}/threads")
        resp.raise_for_status()
        return resp.json()


@router.get("/threads/{thread_id}/messages")
async def get_messages(thread_id: str, request: Request, limit: int = 50):
    _user_id(request)  # auth check
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_CONV_URL}/threads/{thread_id}/messages", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, request: Request):
    user_id = _user_id(request)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(f"{_CONV_URL}/threads/{thread_id}", params={"user_id": user_id})
        resp.raise_for_status()
