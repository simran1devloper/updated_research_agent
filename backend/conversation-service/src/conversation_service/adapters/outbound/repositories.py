"""SQLAlchemy implementations of thread and message repositories."""
import uuid
from datetime import datetime
from sqlalchemy import select, delete
from ...domain.models import Thread, Message
from ...domain.ports import IThreadRepository, IMessageRepository
from ...db.tables import ThreadRow, MessageRow
from ...db.session import SessionLocal


def _thread(row: ThreadRow) -> Thread:
    return Thread(id=row.id, user_id=row.user_id, title=row.title, created_at=row.created_at)


def _message(row: MessageRow) -> Message:
    return Message(id=row.id, thread_id=row.thread_id, role=row.role,
                   content=row.content, metadata=row.meta, created_at=row.created_at)


class SQLThreadRepository(IThreadRepository):
    async def get_or_create(self, thread_id: str, user_id: str, title: str) -> Thread:
        async with SessionLocal() as s:
            row = await s.get(ThreadRow, thread_id)
            if not row:
                row = ThreadRow(id=thread_id, user_id=user_id, title=title or "New conversation")
                s.add(row)
                await s.commit()
                await s.refresh(row)
            return _thread(row)

    async def get(self, thread_id: str) -> Thread | None:
        async with SessionLocal() as s:
            row = await s.get(ThreadRow, thread_id)
            return _thread(row) if row else None

    async def list_for_user(self, user_id: str) -> list[Thread]:
        async with SessionLocal() as s:
            result = await s.execute(
                select(ThreadRow).where(ThreadRow.user_id == user_id)
                .order_by(ThreadRow.created_at.desc())
            )
            return [_thread(r) for r in result.scalars()]

    async def delete(self, thread_id: str, user_id: str) -> None:
        async with SessionLocal() as s:
            await s.execute(
                delete(ThreadRow).where(ThreadRow.id == thread_id, ThreadRow.user_id == user_id)
            )
            await s.commit()


class SQLMessageRepository(IMessageRepository):
    async def append(self, message: Message) -> Message:
        async with SessionLocal() as s:
            row = MessageRow(
                id=message.id or str(uuid.uuid4()),
                thread_id=message.thread_id,
                role=message.role,
                content=message.content,
                meta=message.metadata,
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return _message(row)

    async def list_for_thread(self, thread_id: str, limit: int = 50) -> list[Message]:
        async with SessionLocal() as s:
            result = await s.execute(
                select(MessageRow).where(MessageRow.thread_id == thread_id)
                .order_by(MessageRow.created_at.asc())
                .limit(limit)
            )
            return [_message(r) for r in result.scalars()]

    async def delete_for_thread(self, thread_id: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(MessageRow).where(MessageRow.thread_id == thread_id))
            await s.commit()
