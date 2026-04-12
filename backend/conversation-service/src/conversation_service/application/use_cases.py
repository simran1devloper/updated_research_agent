"""Application use-cases for the Conversation Service."""
import uuid
from ..domain.models import Thread, Message
from ..domain.ports import IThreadRepository, IMessageRepository


class EnsureThreadUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, thread_id: str, user_id: str, title: str = "") -> Thread:
        return await self._repo.get_or_create(thread_id, user_id, title)


class AppendMessageUseCase:
    def __init__(self, thread_repo: IThreadRepository, msg_repo: IMessageRepository) -> None:
        self._threads = thread_repo
        self._msgs = msg_repo

    async def execute(self, thread_id: str, role: str, content: str, metadata: str = "") -> Message:
        msg = Message(id=str(uuid.uuid4()), thread_id=thread_id, role=role,
                      content=content, metadata=metadata)
        return await self._msgs.append(msg)


class GetHistoryUseCase:
    def __init__(self, repo: IMessageRepository) -> None:
        self._repo = repo

    async def execute(self, thread_id: str, limit: int = 50) -> list[Message]:
        return await self._repo.list_for_thread(thread_id, limit=limit)


class ListThreadsUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: str) -> list[Thread]:
        return await self._repo.list_for_user(user_id)


class DeleteThreadUseCase:
    def __init__(self, thread_repo: IThreadRepository, msg_repo: IMessageRepository) -> None:
        self._threads = thread_repo
        self._msgs = msg_repo

    async def execute(self, thread_id: str, user_id: str) -> None:
        await self._msgs.delete_for_thread(thread_id)
        await self._threads.delete(thread_id, user_id)
