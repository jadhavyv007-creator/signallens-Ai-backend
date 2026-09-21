"""
Database engine configuration, session management, and connectivity verification.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from api.config.env import env
from api.database.models import Base

# Database engine configuration
engine = create_async_engine(
    env.effective_database_url,
    echo=env.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


_db_initialized = False


async def init_db() -> None:
    """Initializes database tables on application startup."""
    global _db_initialized
    if not _db_initialized:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            _db_initialized = True
        except Exception as e:
            print(f"⚠️ init_db warning: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    if not _db_initialized:
        await init_db()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Verifies database connectivity for readiness probes (/ready)."""
    try:
        if not _db_initialized:
            await init_db()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"⚠️ DB Health check failed: {e}")
        return False

