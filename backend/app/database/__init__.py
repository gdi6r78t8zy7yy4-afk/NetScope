# NetScope Database Module

"""
Database session management and base models.
"""

import asyncio

from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.base import Base, init_db

__all__ = ["Base", "init_db", "AsyncSession", "get_async_session", "engine"]

# Create async engine with proper connection pooling
_engine: Optional[AsyncSession] = None


def get_engine() -> AsyncSession:
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Prevent stale connections
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
    return _engine


# Create session factory
AsyncSessionLocal = sessionmaker(
    bind=get_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
)


# Export engine for backwards compatibility
engine = get_engine()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Yields:
        AsyncSession: Database session
    
    Raises:
        RuntimeError: If database is not initialized
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized")
    
    session = AsyncSessionLocal()
    try:
        yield session
        # Commit only if not closed and has changes
        if not session.is_active and session.dirty:
            await session.commit()
    except Exception as e:
        if session.is_active:
            await session.rollback()
        raise
    finally:
        await session.close()


async def get_transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a session that requires explicit commit.
    
    Use this for operations that need manual transaction control.
    
    Yields:
        AsyncSession: Database session
    """
    async with get_async_session() as session:
        yield session


async def execute_with_retry(
    func, *args, max_retries: int = 3, **kwargs
) -> any:
    """
    Execute a database function with retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        max_retries: Maximum number of retries on connection failure
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the async function
    
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            async with get_async_session() as session:
                kwargs["session"] = session
                result = await func(*args, **kwargs)
                return result
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (2**attempt))  # Exponential backoff
    
    raise last_exception


async def init_db_with_retry(max_retries: int = 3) -> None:
    """
    Initialize database with retry logic.
    
    Args:
        max_retries: Maximum number of attempts
    
    Raises:
        Exception: If initialization fails after all retries
    """
    for attempt in range(max_retries):
        try:
            await init_db()
            return
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2**attempt))
            else:
                raise
