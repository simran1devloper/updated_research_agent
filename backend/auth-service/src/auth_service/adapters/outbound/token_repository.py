"""SQLAlchemy implementation of IRefreshTokenRepository."""
from sqlalchemy import select, delete
from ...domain.ports import IRefreshTokenRepository
from ...db.tables import RefreshTokenRow
from ...db.session import SessionLocal


class SQLRefreshTokenRepository(IRefreshTokenRepository):
    async def save(self, user_id: str, token_hash: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(RefreshTokenRow).where(RefreshTokenRow.user_id == user_id))
            s.add(RefreshTokenRow(token_hash=token_hash, user_id=user_id))
            await s.commit()

    async def exists(self, token_hash: str) -> bool:
        async with SessionLocal() as s:
            row = await s.get(RefreshTokenRow, token_hash)
            return row is not None

    async def revoke(self, token_hash: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash))
            await s.commit()

    async def revoke_all_for_user(self, user_id: str) -> None:
        async with SessionLocal() as s:
            await s.execute(delete(RefreshTokenRow).where(RefreshTokenRow.user_id == user_id))
            await s.commit()
