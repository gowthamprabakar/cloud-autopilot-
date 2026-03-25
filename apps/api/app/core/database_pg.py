"""
Database configuration supporting both SQLite (dev) and PostgreSQL (prod).

Reads DATABASE_URL from environment:
  - postgresql://  -> uses asyncpg driver (postgresql+asyncpg://)
  - sqlite://      -> uses aiosqlite driver (current dev behavior)

Sprint 29 — OmniSec Infrastructure
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Resolve the async-compatible database URL
# ---------------------------------------------------------------------------

_raw_url: str = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./omnisec_dev.db",
)


def _resolve_async_url(url: str) -> str:
    """Convert a plain database URL to its async-driver equivalent."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        # Heroku-style shorthand
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


DATABASE_URL: str = _resolve_async_url(_raw_url)

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_is_sqlite: bool = DATABASE_URL.startswith("sqlite")
_is_dev: bool = os.getenv("API_ENV", "development") == "development"

_engine_kwargs: dict = {"echo": _is_dev}

if not _is_sqlite:
    # PostgreSQL connection-pool tuning
    _engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,  # recycle connections every 30 min
        }
    )

engine: AsyncEngine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async session; commit on success, rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
