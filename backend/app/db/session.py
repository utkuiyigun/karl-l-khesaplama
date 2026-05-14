"""
Async SQLAlchemy engine + session factory.

FastAPI dependency olarak `get_db()` kullanılır:

    from fastapi import Depends
    from app.db.session import get_db

    @router.get("/...")
    async def endpoint(db: AsyncSession = Depends(get_db)):
        ...
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — request başına bir session."""
    async with AsyncSessionLocal() as session:
        yield session
