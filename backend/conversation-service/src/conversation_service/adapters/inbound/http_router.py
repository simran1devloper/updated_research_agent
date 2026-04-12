"""Inbound HTTP adapter — conversation REST endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ...container import ConversationContainer

router = APIRouter(tags=["conversations"])


class ThreadOut(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str


class MessageOut(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    created_at: str


def _c() -> ConversationContainer:
    return ConversationContainer.instance()


def _thread_out(t) -> ThreadOut:
    return ThreadOut(id=t.id, user_id=t.user_id, title=t.title,
                     created_at=t.created_at.isoformat())


def _msg_out(m) -> MessageOut:
    return MessageOut(id=m.id, thread_id=m.thread_id, role=m.role,
                      content=m.content, created_at=m.created_at.isoformat())


@router.get("/users/{user_id}/threads", response_model=list[ThreadOut])
async def list_threads(user_id: str):
    threads = await _c().list_threads_use_case().execute(user_id)
    return [_thread_out(t) for t in threads]


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
async def get_messages(thread_id: str, limit: int = 50):
    messages = await _c().get_history_use_case().execute(thread_id, limit=limit)
    return [_msg_out(m) for m in messages]


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(thread_id: str, user_id: str):
    await _c().delete_thread_use_case().execute(thread_id, user_id)


@router.get("/conversation/health")
async def health():
    return {"service": "conversation-service", "status": "ok"}
