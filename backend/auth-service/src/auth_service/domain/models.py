"""Domain models for the Auth Service."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"


@dataclass
class User:
    id: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    hashed_password: str | None = None          # None for OAuth-only users
    oauth_provider: OAuthProvider | None = None
    oauth_sub: str | None = None                # provider's subject ID
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass
class TokenClaims:
    user_id: str
    email: str
    role: str
    valid: bool
    error: str = ""
