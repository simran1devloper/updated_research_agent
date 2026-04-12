"""Application use-cases for the Auth Service."""
from ..domain.models import User, TokenPair, TokenClaims, OAuthProvider
from ..domain.service import AuthDomainService
from ..domain.ports import IUserRepository


class RegisterUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    async def execute(self, email: str, username: str, password: str) -> User:
        return await self._svc.register(email, username, password)


class LoginUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    async def execute(self, email: str, password: str) -> TokenPair:
        return await self._svc.login(email, password)


class RefreshUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    async def execute(self, refresh_token: str) -> TokenPair:
        return await self._svc.refresh(refresh_token)


class LogoutUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    async def execute(self, refresh_token: str) -> None:
        await self._svc.logout(refresh_token)


class OAuthLoginUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    async def execute(self, provider: OAuthProvider, sub: str, email: str, username: str) -> TokenPair:
        return await self._svc.oauth_login(provider, sub, email, username)


class ValidateTokenUseCase:
    def __init__(self, svc: AuthDomainService) -> None:
        self._svc = svc

    def execute(self, token: str) -> TokenClaims:
        return self._svc.validate_token(token)


# ── User management ──────────────────────────────────────────────────────────

class GetUserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: str) -> User | None:
        return await self._repo.get_by_id(user_id)


class ListUsersUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, skip: int = 0, limit: int = 50) -> list[User]:
        return await self._repo.list_users(skip=skip, limit=limit)


class UpdateUserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, user: User) -> User:
        return await self._repo.update(user)


class DeleteUserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: str) -> None:
        await self._repo.delete(user_id)
