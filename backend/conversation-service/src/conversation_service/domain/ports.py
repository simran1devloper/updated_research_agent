"""Ports for the Conversation Service domain."""
from abc import ABC, abstractmethod
from .models import Thread, Message


class IThreadRepository(ABC):
    @abstractmethod
    async def get_or_create(self, thread_id: str, user_id: str, title: str) -> Thread: ...

    @abstractmethod
    async def get(self, thread_id: str) -> Thread | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[Thread]: ...

    @abstractmethod
    async def delete(self, thread_id: str, user_id: str) -> None: ...


class IMessageRepository(ABC):
    @abstractmethod
    async def append(self, message: Message) -> Message: ...

    @abstractmethod
    async def list_for_thread(self, thread_id: str, limit: int = 50) -> list[Message]: ...

    @abstractmethod
    async def delete_for_thread(self, thread_id: str) -> None: ...
