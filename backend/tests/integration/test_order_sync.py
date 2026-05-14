"""
Sipariş senkronizasyon servisi integration testleri.

Strateji:
- Test DB'sinde gerçek Customer + PlatformConnection oluştur
- TrendyolClient.list_orders'ı fixture döndürecek şekilde mock'la
- services.order_sync.AsyncSessionLocal'ı test_session_factory'e yönlendir
- sync_connection_orders'ı çağır → DB'de orders/packages/items doğrula
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.adapters.trendyol.client import TrendyolClient
from app.core.security import encrypt_secret
from app.models.customer import Customer
from app.models.order import Order as OrderModel
from app.models.order_item import OrderItem as OrderItemModel
from app.models.platform_connection import PlatformConnection
from app.models.shipment_package import ShipmentPackage as ShipmentPackageModel
from app.services.order_sync import sync_connection_orders

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "trendyol_orders"


@pytest.fixture
def orders_page() -> dict:
    return json.loads((FIXTURE_DIR / "orders_page_sample.json").read_text())


@pytest.fixture
def mock_trendyol_and_session(monkeypatch, orders_page, test_session_factory):
    """TrendyolClient'ı fixture'a, AsyncSessionLocal'ı test factory'e patch'le."""

    async def _mock_list_orders(self, **kwargs):  # noqa: ARG001
        return orders_page

    monkeypatch.setattr(TrendyolClient, "list_orders", _mock_list_orders)
    monkeypatch.setattr(
        "app.services.order_sync.AsyncSessionLocal", test_session_factory
    )


async def _setup_customer_and_connection(db_session, email: str) -> int:
    """Yardımcı: customer + aktif connection yarat, connection.id döndür."""
    customer = Customer(email=email, name=f"Sync test ({email})")
    db_session.add(customer)
    await db_session.commit()

    conn = PlatformConnection(
        customer_id=customer.id,
        platform="trendyol",
        seller_id="seller-X",
        api_key_encrypted=encrypt_secret("api-key-xyz"),
        api_secret_encrypted=encrypt_secret("api-secret-abc"),
        is_active=True,
        sync_start_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(conn)
    await db_session.commit()
    return conn.id


async def test_sync_writes_orders_packages_items(
    db_session, mock_trendyol_and_session
) -> None:
    """4 sipariş, 5 paket (1+1+1+2), toplam 5 kalem (1+1+1+2) DB'ye yazılmalı."""
    conn_id = await _setup_customer_and_connection(db_session, "sync1@test.com")

    result = await sync_connection_orders(conn_id)
    assert result["orders_processed"] == 4

    orders = (
        await db_session.execute(
            select(OrderModel).where(OrderModel.platform_connection_id == conn_id)
        )
    ).scalars().all()
    assert len(orders) == 4

    # Order 4 → 2 paket
    o4 = next(o for o in orders if o.external_id == "TY-2026-004")
    packages = (
        await db_session.execute(
            select(ShipmentPackageModel).where(ShipmentPackageModel.order_id == o4.id)
        )
    ).scalars().all()
    assert len(packages) == 2

    # Toplam item sayısı: 1+1+1+2 = 5
    items = (
        await db_session.execute(
            select(OrderItemModel).where(
                OrderItemModel.order_id.in_([o.id for o in orders])
            )
        )
    ).scalars().all()
    assert len(items) == 5


async def test_sync_updates_last_sync_at(
    db_session, mock_trendyol_and_session
) -> None:
    """Başarılı sync sonrası PlatformConnection.last_sync_at güncellenmeli."""
    conn_id = await _setup_customer_and_connection(db_session, "lastsync@test.com")

    before = datetime.now(timezone.utc)
    await sync_connection_orders(conn_id)

    db_session.expire_all()
    conn = await db_session.get(PlatformConnection, conn_id)
    assert conn.last_sync_at is not None
    assert conn.last_sync_at >= before


async def test_sync_is_idempotent(db_session, mock_trendyol_and_session) -> None:
    """İkinci sync sonrası DB'de duplicate yok (upsert davranışı)."""
    conn_id = await _setup_customer_and_connection(db_session, "idem@test.com")

    await sync_connection_orders(conn_id)
    await sync_connection_orders(conn_id)

    orders = (
        await db_session.execute(
            select(OrderModel).where(OrderModel.platform_connection_id == conn_id)
        )
    ).scalars().all()
    assert len(orders) == 4, "İdempotency bozuldu: ikinci sync kayıt çoğalttı"


async def test_sync_skips_inactive_connection(
    db_session, mock_trendyol_and_session
) -> None:
    conn_id = await _setup_customer_and_connection(db_session, "inactive@test.com")
    conn = await db_session.get(PlatformConnection, conn_id)
    conn.is_active = False
    await db_session.commit()

    result = await sync_connection_orders(conn_id)
    assert result.get("skipped") == "inactive_or_missing"

    orders = (
        await db_session.execute(
            select(OrderModel).where(OrderModel.platform_connection_id == conn_id)
        )
    ).scalars().all()
    assert len(orders) == 0
