"""
Pytest fixture'ları.

Test DB stratejisi:
- Production DB ile aynı postgres sunucusunda ayrı bir DB: `melon_kar_test`
- Migration `alembic upgrade head` ile test DB'ye uygulanmıştır
- Her test başında app tabloları TRUNCATE edilir (alembic_version'a dokunulmaz)
- AsyncClient ASGI transport üzerinden FastAPI'ye doğrudan istek atar, ağ yok
"""
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401 — Base.metadata'ya kayıt
    Customer,
    Order,
    OrderItem,
    PlatformConnection,
    Product,
    ShipmentPackage,
)


def _test_database_url() -> str:
    """Üretim URL'inin sonundaki DB adını 'melon_kar_test' ile değiştir."""
    base, _ = settings.database_url.rsplit("/", 1)
    return f"{base}/melon_kar_test"


TEST_DATABASE_URL = _test_database_url()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncIterator:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _truncate_tables(test_engine) -> None:
    """Her test başında app tablolarını temizle (alembic_version hariç)."""
    table_names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db_session(test_session_factory) -> AsyncIterator[AsyncSession]:
    """Test içinde DB'ye doğrudan erişim — assertion'lar için."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client(test_session_factory) -> AsyncIterator[AsyncClient]:
    """FastAPI test client — get_db dependency'sini test DB'ye yönlendirir."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()
