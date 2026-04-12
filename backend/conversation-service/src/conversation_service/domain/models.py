"""Domain models for the Conversation Service."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Thread:
    id: str
    user_id: str
    title: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    id: str
    thread_id: str
    role: str           # "user" | "assistant"
    content: str
    metadata: str = ""  # JSON string
    created_at: datetime = field(default_factory=datetime.utcnow)
