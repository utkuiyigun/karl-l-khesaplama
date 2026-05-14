"""
COGS yükleme integration testleri.

- Geçerli CSV → Product oluşturulur veya güncellenir
- Aktif Trendyol bağlantısı yoksa hata
- Geçersiz format / kolon eksik → 400
- Sync sırasında COGS yüklü ürünlerin cogs_snapshot'ı orderitem'a doğru kopyalanır
"""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.trendyol.client import TrendyolClient
from app.core.security import encrypt_secret
from app.models.customer import Customer
from app.models.order_item import OrderItem as OrderItemModel
from app.models.platform_connection import PlatformConnection
from app.models.product import Product
from app.services.order_sync import sync_connection_orders

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "trendyol_orders"


async def _setup_customer_with_connection(
    db_session: AsyncSession, email: str
) -> tuple[int, int]:
    customer = Customer(email=email, name=f"COGS test ({email})")
    db_session.add(customer)
    await db_session.commit()

    conn = PlatformConnection(
        customer_id=customer.id,
        platform="trendyol",
        seller_id="cogs-seller",
        api_key_encrypted=encrypt_secret("k"),
        api_secret_encrypted=encrypt_secret("s"),
        is_active=True,
        sync_start_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(conn)
    await db_session.commit()
    return customer.id, conn.id


async def test_template_download(client: AsyncClient) -> None:
    """Template endpoint CSV döner ve barcode/cogs kolonlarını içerir."""
    response = await client.get("/api/v1/customers/1/cogs/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "barcode" in body and "cogs" in body


async def test_upload_csv_creates_products(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Geçerli CSV → yeni ürünler placeholder olarak oluşturulur."""
    customer_id, _ = await _setup_customer_with_connection(db_session, "cogs1@test.com")

    csv_body = (
        "barcode,name,cogs\n"
        "BAR-001,Urun A,15.00\n"
        "BAR-002,Urun B,30.50\n"
    )
    files = {"file": ("cogs.csv", csv_body.encode("utf-8"), "text/csv")}
    response = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["created"] == 2
    assert result["updated"] == 0
    assert result["errors"] == []

    products = (
        await db_session.execute(
            select(Product).where(Product.customer_id == customer_id)
        )
    ).scalars().all()
    assert len(products) == 2
    barcodes = {p.barcode: p.cogs for p in products}
    assert barcodes["BAR-001"] == Decimal("15.00")
    assert barcodes["BAR-002"] == Decimal("30.50")


async def test_upload_updates_existing_products(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Var olan barkod için ikinci yükleme update sayılır."""
    customer_id, _ = await _setup_customer_with_connection(db_session, "cogs2@test.com")

    csv1 = "barcode,cogs\nBAR-X,10.00\n"
    files = {"file": ("v1.csv", csv1.encode(), "text/csv")}
    r1 = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)
    assert r1.json()["created"] == 1

    csv2 = "barcode,cogs\nBAR-X,25.00\n"
    files = {"file": ("v2.csv", csv2.encode(), "text/csv")}
    r2 = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)
    body = r2.json()
    assert body["updated"] == 1
    assert body["created"] == 0

    product = (
        await db_session.execute(
            select(Product).where(
                Product.customer_id == customer_id, Product.barcode == "BAR-X"
            )
        )
    ).scalar_one()
    assert product.cogs == Decimal("25.00")


async def test_upload_rejects_missing_required_column(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer_id, _ = await _setup_customer_with_connection(db_session, "cogs3@test.com")

    csv_body = "barcode\nBAR-001\n"  # cogs kolonu yok
    files = {"file": ("bad.csv", csv_body.encode(), "text/csv")}
    response = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)
    assert response.status_code == 400
    assert "cogs" in response.json()["detail"].lower()


async def test_upload_rejects_unsupported_extension(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer_id, _ = await _setup_customer_with_connection(db_session, "cogs4@test.com")

    files = {"file": ("doc.txt", b"barcode,cogs\nA,1\n", "text/plain")}
    response = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)
    assert response.status_code == 400


async def test_upload_requires_active_connection(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Aktif Trendyol bağlantısı yoksa hata."""
    customer = Customer(email="no-conn@test.com", name="No Conn")
    db_session.add(customer)
    await db_session.commit()

    csv_body = "barcode,cogs\nBAR-001,10.00\n"
    files = {"file": ("cogs.csv", csv_body.encode(), "text/csv")}
    response = await client.post(f"/api/v1/customers/{customer.id}/cogs", files=files)
    assert response.status_code == 400
    assert "trendyol" in response.json()["detail"].lower()


async def test_upload_reports_validation_errors_per_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer_id, _ = await _setup_customer_with_connection(db_session, "cogs5@test.com")

    csv_body = (
        "barcode,cogs\n"
        "BAR-OK,10.00\n"
        ",5.00\n"               # boş barcode
        "BAR-NEG,-1.00\n"       # negatif
        "BAR-BAD,not-a-number\n"
    )
    files = {"file": ("mixed.csv", csv_body.encode(), "text/csv")}
    response = await client.post(f"/api/v1/customers/{customer_id}/cogs", files=files)
    assert response.status_code == 200
    body = response.json()
    assert len(body["errors"]) == 3
    # Errors → rollback → hiçbir kayıt yazılmadı
    assert body["created"] == 0
    products = (
        await db_session.execute(
            select(Product).where(Product.customer_id == customer_id)
        )
    ).scalars().all()
    assert len(products) == 0


async def test_sync_uses_uploaded_cogs_for_item_snapshot(
    db_session: AsyncSession, mock_trendyol_and_session
) -> None:
    """COGS yüklendikten sonra sync, OrderItem.cogs_snapshot'ı doğru doldurmalı."""
    customer = Customer(email="snap@test.com", name="Snap")
    db_session.add(customer)
    await db_session.commit()

    conn = PlatformConnection(
        customer_id=customer.id,
        platform="trendyol",
        seller_id="snap-seller",
        api_key_encrypted=encrypt_secret("k"),
        api_secret_encrypted=encrypt_secret("s"),
        is_active=True,
        sync_start_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(conn)
    await db_session.commit()

    # ANON-BAR-001 fixture'ında order #1 (Delivered) için kullanılıyor
    cogs_product = Product(
        customer_id=customer.id,
        platform_connection_id=conn.id,
        external_id="ANON-BAR-001",
        barcode="ANON-BAR-001",
        name="Test product",
        cogs=Decimal("40.00"),
    )
    db_session.add(cogs_product)
    await db_session.commit()

    # Sync (mock_trendyol_and_session conftest'tan değil, kendi test fixture'ım. Düzeltmem lazım.)
    await sync_connection_orders(conn.id)

    item = (
        await db_session.execute(
            select(OrderItemModel).where(
                OrderItemModel.customer_id == customer.id,
                OrderItemModel.barcode == "ANON-BAR-001",
            )
        )
    ).scalar_one()
    assert item.cogs_snapshot == Decimal("40.00"), "COGS lookup snapshot'a kopyalanmadı"
    assert item.product_id == cogs_product.id


@pytest.fixture
def mock_trendyol_and_session(monkeypatch, test_session_factory):
    """COGS-aware sync test'leri için Trendyol mock + session redirect."""

    async def _mock_list_orders(self, **kwargs):  # noqa: ARG001
        return json.loads((FIXTURE_DIR / "orders_page_sample.json").read_text())

    monkeypatch.setattr(TrendyolClient, "list_orders", _mock_list_orders)
    monkeypatch.setattr(
        "app.services.order_sync.AsyncSessionLocal", test_session_factory
    )
