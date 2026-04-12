"""SQLAlchemy implementation of IUserRepository."""
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain.models import User, UserRole, OAuthProvider
from ...domain.ports import IUserRepository
from ...db.tables import UserRow
from ...db.session import SessionLocal


def _to_domain(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        username=row.username,
        role=UserRole(row.role),
        is_active=row.is_active,
        hashed_password=row.hashed_password,
        oauth_provider=OAuthProvider(row.oauth_provider) if row.oauth_provider else None,
        oauth_sub=row.oauth_sub,
        created_at=row.created_at,
    )


def _to_row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
        hashed_password=user.hashed_password,
        oauth_provider=user.oauth_provider.value if user.oauth_provider else None,
        oauth_sub=user.oauth_sub,
        created_at=user.created_at,
    )


class SQLUserRepository(IUserRepository):
    async def create(self, user: User) -> User:
        async with SessionLocal() as s:
            row = _to_row(user)
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return _to_domain(row)

    async def get_by_id(self, user_id: str) -> User | None:
        async with SessionLocal() as s:
            row = await s.get(UserRow, user_id)
            return _to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        async with SessionLocal() as s:
            result = await s.execute(select(UserRow).where(UserRow.email == email))
            row = result.scalar_one_or_none()
            return _to_domain(row) if row else None

    async def get_by_oauth(self, provider: OAuthProvider, sub: str) -> User | None:
        async with SessionLocal() as s:
            result = await s.execute(
                select(UserRow).where(
                    UserRow.oauth_provider == provider.value,
                    UserRow.oauth_sub == sub,
                )
            )
            row = result.scalar_one_or_none()
            return _to_domain(row) if row else None

    async def update(self, user: User) -> User:
        async with SessionLocal() as s:
            row = await s.get(UserRow, user.id)
            if not row:
                raise ValueError("User not found")
            row.email = user.email
            row.username = user.username
            row.role = user.role.value
            row.is_active = user.is_active
            row.hashed_password = user.hashed_password
            row.oauth_provider = user.oauth_provider.value if user.oauth_provider else None
            row.oauth_sub = user.oauth_sub
            await s.commit()
            await s.refresh(row)
            return _to_domain(row)

    async def delete(self, user_id: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(UserRow).where(UserRow.id == user_id))
            await s.commit()

    async def list_users(self, skip: int = 0, limit: int = 50) -> list[User]:
        async with SessionLocal() as s:
            result = await s.execute(select(UserRow).offset(skip).limit(limit))
            return [_to_domain(r) for r in result.scalars()]
