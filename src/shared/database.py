"""Database setup — SQLAlchemy 2.0 async engine + session factory for TimescaleDB."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.shared.config import settings

logger = logging.getLogger(__name__)


def _build_async_url(url: str) -> str:
    """Convert a sync database URL to the appropriate async driver variant.

    Args:
        url: A database URL (postgresql://, sqlite://, or already async).

    Returns:
        URL with the async driver scheme required by SQLAlchemy async.
    """
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
    url = re.sub(r"^postgresql\+psycopg2://", "postgresql+asyncpg://", url)
    return url


_async_url = _build_async_url(settings.database_url)
_is_sqlite = _async_url.startswith("sqlite")

_engine_kwargs: dict[str, object] = {
    "echo": False,
}
if not _is_sqlite:
    _engine_kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20, pool_recycle=3600)

async_engine = create_async_engine(_async_url, **_engine_kwargs)  # type: ignore[arg-type]

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection.

    Automatically commits on success and rolls back on any exception.

    Yields:
        An open AsyncSession bound to the shared connection pool.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Database session rolled back due to an unhandled exception")
            raise


async def create_all_tables() -> None:
    """Create all ORM-mapped tables against the live database.

    Intended for development and testing only. Use Alembic for production
    migrations.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created (dev/test mode)")
