"""Ports for the Auth Service domain."""
from abc import ABC, abstractmethod
from .models import User, TokenPair, TokenClaims, OAuthProvider


class IUserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_oauth(self, provider: OAuthProvider, sub: str) -> User | None: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: str) -> None: ...

    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 50) -> list[User]: ...


class IRefreshTokenRepository(ABC):
    @abstractmethod
    async def save(self, user_id: str, token_hash: str) -> None: ...

    @abstractmethod
    async def exists(self, token_hash: str) -> bool: ...

    @abstractmethod
    async def revoke(self, token_hash: str) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> None: ...


class ITokenService(ABC):
    @abstractmethod
    def create_token_pair(self, user: User) -> TokenPair: ...

    @abstractmethod
    def validate_access_token(self, token: str) -> TokenClaims: ...

    @abstractmethod
    def decode_refresh_token(self, token: str) -> TokenClaims: ...


class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool: ...
