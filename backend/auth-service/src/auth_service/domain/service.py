"""Auth domain service — core business logic."""
import uuid
import hashlib
from .models import User, UserRole, TokenPair, TokenClaims, OAuthProvider
from .ports import IUserRepository, IRefreshTokenRepository, ITokenService, IPasswordHasher


class AuthDomainService:
    def __init__(
        self,
        user_repo: IUserRepository,
        token_repo: IRefreshTokenRepository,
        token_svc: ITokenService,
        hasher: IPasswordHasher,
    ) -> None:
        self._users = user_repo
        self._tokens = token_repo
        self._token_svc = token_svc
        self._hasher = hasher

    async def register(self, email: str, username: str, password: str) -> User:
        if await self._users.get_by_email(email):
            raise ValueError("Email already registered")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            role=UserRole.USER,
            is_active=True,
            hashed_password=self._hasher.hash(password),
        )
        return await self._users.create(user)

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        if not user or not user.hashed_password:
            raise ValueError("Invalid credentials")
        if not self._hasher.verify(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account disabled")
        pair = self._token_svc.create_token_pair(user)
        await self._tokens.save(user.id, _hash(pair.refresh_token))
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = self._token_svc.decode_refresh_token(refresh_token)
        if not claims.valid:
            raise ValueError(claims.error)
        if not await self._tokens.exists(_hash(refresh_token)):
            raise ValueError("Token revoked or unknown")
        user = await self._users.get_by_id(claims.user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or disabled")
        await self._tokens.revoke(_hash(refresh_token))
        pair = self._token_svc.create_token_pair(user)
        await self._tokens.save(user.id, _hash(pair.refresh_token))
        return pair

    async def logout(self, refresh_token: str) -> None:
        await self._tokens.revoke(_hash(refresh_token))

    async def oauth_login(
        self,
        provider: OAuthProvider,
        sub: str,
        email: str,
        username: str,
    ) -> TokenPair:
        user = await self._users.get_by_oauth(provider, sub)
        if not user:
            # auto-provision on first OAuth login
            existing = await self._users.get_by_email(email)
            if existing:
                # link provider to existing account
                existing.oauth_provider = provider
                existing.oauth_sub = sub
                user = await self._users.update(existing)
            else:
                user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    username=username,
                    role=UserRole.USER,
                    is_active=True,
                    oauth_provider=provider,
                    oauth_sub=sub,
                )
                user = await self._users.create(user)
        if not user.is_active:
            raise ValueError("Account disabled")
        pair = self._token_svc.create_token_pair(user)
        await self._tokens.save(user.id, _hash(pair.refresh_token))
        return pair

    def validate_token(self, token: str) -> TokenClaims:
        return self._token_svc.validate_access_token(token)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
