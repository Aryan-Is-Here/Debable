"""Async engine, session factory and the FastAPI ``get_db`` dependency.

The engine is created lazily and memoised so that importing this module never opens a
connection — tests and Alembic import the app without a live database.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session, rolling back if the handler raises.

    Handlers commit explicitly; leaving commit to the dependency would hide write
    failures behind an already-sent response.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """A session for one unit of work, outside the request/response cycle.

    ``get_db`` is a FastAPI dependency and lives as long as its handler. That is right for
    an HTTP request and wrong for a WebSocket, which stays open for the whole debate: a
    dependency-scoped session would pin a pool connection through an hour of idle chat.
    Socket handlers open one of these per unit of work instead — authenticate, then each
    message — and hold nothing in between.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SessionScope = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def get_session_scope() -> SessionScope:
    """Dependency returning the scope factory itself, not a session.

    The indirection exists so tests can substitute a factory that hands back their single
    transactional session; depending on ``session_scope`` directly would leave no seam.
    """
    return session_scope


async def dispose_engine() -> None:
    """Close pooled connections. Called on application shutdown."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
