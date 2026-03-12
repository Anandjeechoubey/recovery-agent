"""Database engine and session management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.db.models import Base

engine = create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine connection pool."""
    await engine.dispose()


def get_session() -> AsyncSession:
    """Create a new async session."""
    return async_session()
