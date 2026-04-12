"""Ports for the Research Service domain."""
from abc import ABC, abstractmethod


class IIntentClientPort(ABC):
    @abstractmethod
    async def classify(self, query: str, history: list[dict]) -> dict: ...


class IMemoryClientPort(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5, user_id: str = "") -> list[str]: ...

    @abstractmethod
    async def store(self, query_id: str, query: str, response: str, user_id: str = "") -> None: ...


class ISearchClientPort(ABC):
    @abstractmethod
    async def search(self, query: str, sites: list[str] | None = None, limit: int = 5) -> list[dict]: ...


class ISynthesisClientPort(ABC):
    @abstractmethod
    async def synthesize(self, query: str, research_data: list[dict], history: list[dict], gaps: list[str]) -> dict: ...

    @abstractmethod
    async def synthesize_stream(self, query: str, research_data: list[dict], history: list[dict], gaps: list[str]): ...

    @abstractmethod
    async def analyze_gaps(self, query: str, research_data: list[dict], iteration: int) -> dict: ...


class IConversationClientPort(ABC):
    @abstractmethod
    async def ensure_thread(self, thread_id: str, user_id: str, title: str = "") -> None: ...

    @abstractmethod
    async def append_message(self, thread_id: str, role: str, content: str, metadata: str = "") -> None: ...

    @abstractmethod
    async def get_history(self, thread_id: str, limit: int = 20) -> list[dict]: ...
