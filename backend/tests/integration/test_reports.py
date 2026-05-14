"""
Raporlama endpoint'leri integration testleri.

End-to-end zincir: Trendyol fixture → sync → DB → reports endpoint → kâr hesabı.
"""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.trendyol.client import TrendyolClient
from app.core.security import encrypt_secret
from app.models.customer import Customer
from app.models.platform_connection import PlatformConnection
from app.models.product import Product
from app.services.order_sync import sync_connection_orders

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "trendyol_orders"


@pytest.fixture
def trendyol_mocked(monkeypatch, test_session_factory):
    """Trendyol API'sini fixture'a yönlendir + AsyncSessionLocal'ı test factory'e patch'le."""

    async def _mock(self, **kwargs):  # noqa: ARG001
        return json.loads((FIXTURE_DIR / "orders_page_sample.json").read_text())

    monkeypatch.setattr(TrendyolClient, "list_orders", _mock)
    monkeypatch.setattr(
        "app.services.order_sync.AsyncSessionLocal", test_session_factory
    )


async def _setup_synced_customer(
    db_session: AsyncSession, email: str, *, with_cogs: bool = True
) -> int:
    """Müşteri yarat, bağlantı kur, COGS yükle, sync et. customer_id döner."""
    customer = Customer(
        email=email,
        name=f"Report test ({email})",
        stopaj_rate=Decimal("0"),
    )
    db_session.add(customer)
    await db_session.commit()

    conn = PlatformConnection(
        customer_id=customer.id,
        platform="trendyol",
        seller_id="report-seller",
        api_key_encrypted=encrypt_secret("k"),
        api_secret_encrypted=encrypt_secret("s"),
        is_active=True,
        sync_start_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(conn)
    await db_session.commit()

    if with_cogs:
        # Order #1'in barkodu için COGS yüklü ürün
        db_session.add(
            Product(
                customer_id=customer.id,
                platform_connection_id=conn.id,
                external_id="ANON-BAR-001",
                barcode="ANON-BAR-001",
                name="Test product",
                cogs=Decimal("40.00"),
            )
        )
        await db_session.commit()

    await sync_connection_orders(conn.id)
    return customer.id


async def test_list_orders_returns_profit_breakdown(
    client: AsyncClient, db_session: AsyncSession, trendyol_mocked
) -> None:
    customer_id = await _setup_synced_customer(db_session, "list@test.com")

    response = await client.get(f"/api/v1/customers/{customer_id}/orders")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4

    # Her satırda profit alanı dolu olmalı
    sample = body["items"][0]
    assert "profit" in sample
    assert "net_profit" in sample["profit"]


async def test_get_order_with_packages_and_items(
    client: AsyncClient, db_session: AsyncSession, trendyol_mocked
) -> None:
    customer_id = await _setup_synced_customer(db_session, "detail@test.com")

    # Order list'ten id al
    list_resp = await client.get(f"/api/v1/customers/{customer_id}/orders")
    delivered_order = next(
        o for o in list_resp.json()["items"] if o["external_id"] == "TY-2026-001"
    )

    detail = await client.get(
        f"/api/v1/customers/{customer_id}/orders/{delivered_order['id']}"
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["external_id"] == "TY-2026-001"
    assert len(body["packages"]) == 1

    profit = body["profit"]
    # COGS=40 yüklü, 100 TL Delivered → net = 12.14
    assert Decimal(profit["net_profit"]) == Decimal("12.14")
    assert Decimal(profit["total_cogs"]) == Decimal("40.00")
    assert profit["is_realized"] is True


async def test_get_order_returns_404_for_other_customer(
    client: AsyncClient, db_session: AsyncSession, trendyol_mocked
) -> None:
    """ADR-008: müşteri başka müşterinin siparişine erişemez."""
    cid_a = await _setup_synced_customer(db_session, "iso-a@test.com")
    cid_b = await _setup_synced_customer(db_session, "iso-b@test.com", with_cogs=False)

    # A'nın siparişlerini al
    list_a = await client.get(f"/api/v1/customers/{cid_a}/orders")
    order_id = list_a.json()["items"][0]["id"]

    # B müşterisinin URL'inden A'nın order'ına erişim → 404
    response = await client.get(f"/api/v1/customers/{cid_b}/orders/{order_id}")
    assert response.status_code == 404


async def test_product_profitability_groups_by_barcode(
    client: AsyncClient, db_session: AsyncSession, trendyol_mocked
) -> None:
    customer_id = await _setup_synced_customer(db_session, "profit@test.com")

    response = await client.get(
        f"/api/v1/customers/{customer_id}/products/profitability"
    )
    assert response.status_code == 200
    rows = response.json()
    # Fixture'da 5 farklı barcode var; her birinin satırı var
    barcodes = {row["barcode"] for row in rows}
    assert "ANON-BAR-001" in barcodes
    assert len(rows) == 5

    # COGS yüklü BAR-001 için item-level: 100 - 18 - 16.67 - 40 = 25.33
    bar_001 = next(r for r in rows if r["barcode"] == "ANON-BAR-001")
    assert Decimal(bar_001["item_net_profit"]) == Decimal("25.33")
    assert Decimal(bar_001["total_cogs"]) == Decimal("40.00")
    assert bar_001["units_sold"] == 1

    # Sıralama net kâra göre desc — kontrol et
    nets = [Decimal(r["item_net_profit"]) for r in rows]
    assert nets == sorted(nets, reverse=True)


async def test_campaign_simulation_decreases_net_profit_with_discount(
    client: AsyncClient, db_session: AsyncSession, trendyol_mocked
) -> None:
    customer_id = await _setup_synced_customer(db_session, "sim@test.com")

    response = await client.post(
        f"/api/v1/customers/{customer_id}/simulations",
        json={"discount_pct": "0.20", "volume_uplift_pct": "0"},
    )
    assert response.status_code == 200
    body = response.json()
    base = Decimal(body["base_net_profit"])
    sim = Decimal(body["simulated_net_profit"])
    delta = Decimal(body["delta"])
    # %20 indirim hacim artışı olmadan → kâr düşer (delta < 0)
    assert delta < 0
    assert sim < base


async def test_simulation_returns_zero_for_customer_without_items(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer = Customer(email="empty@test.com", name="Empty")
    db_session.add(customer)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/customers/{customer.id}/simulations",
        json={"discount_pct": "0.10"},
    )
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["base_net_profit"]) == Decimal("0")
    assert Decimal(body["simulated_net_profit"]) == Decimal("0")
