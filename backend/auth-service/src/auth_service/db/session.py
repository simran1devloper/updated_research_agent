"""Async SQLAlchemy engine + session factory."""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .tables import Base

_DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./auth.db")

engine = create_async_engine(_DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
