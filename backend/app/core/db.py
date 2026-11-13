"""Async database engine and session management."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

# Neon's pooled (-pooler) endpoint is PgBouncer in transaction mode, which
# can't keep asyncpg's named prepared statements across transactions:
# disable the statement cache and use unique names (SQLAlchemy's documented fix).
_pgbouncer_args = (
    {
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }
    if settings.uses_pgbouncer
    else {}
)

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=_pgbouncer_args,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    async with async_session_maker() as session:
        yield session
