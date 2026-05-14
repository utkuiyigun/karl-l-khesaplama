"""
TrendyolAdapter integration testleri.

Stratejisi:
- Gerçek bir Trendyol HTTP çağrısı yapılmaz: TrendyolClient.list_orders
  monkeypatch ile fixture JSON döndürecek şekilde patch'lenir.
- Fixture: tests/fixtures/trendyol_orders/orders_page_sample.json
  Trendyol resmi response şemasına dayalı anonim örnek (4 sipariş).
- Hesaplama motoru üzerinden uçtan uca smoke test de var: adapter → Order → profit.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.base.types import PackageStatus
from app.adapters.trendyol.adapter import (
    DEFAULT_PACKAGE_SERVICE_FEE,
    TrendyolAdapter,
    _map_status,
)
from app.adapters.trendyol.client import TrendyolClient
from app.calculators.profit import calculate_order_profit

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "trendyol_orders"


@pytest.fixture
def orders_page_response() -> dict:
    return json.loads((FIXTURE_DIR / "orders_page_sample.json").read_text())


@pytest.fixture
def adapter_with_mock_client(orders_page_response, monkeypatch) -> TrendyolAdapter:
    """TrendyolClient.list_orders'ı fixture döndürecek şekilde mock'la."""

    async def _mock_list_orders(self, **kwargs):  # noqa: ARG001
        return orders_page_response

    monkeypatch.setattr(TrendyolClient, "list_orders", _mock_list_orders)

    return TrendyolAdapter(
        api_key="test-key",
        api_secret="test-secret",
        seller_id="seller-999",
        customer_id=1,
        platform_connection_id=10,
    )


async def test_fetch_orders_basic_mapping(
    adapter_with_mock_client: TrendyolAdapter,
) -> None:
    """Ham JSON → iç Order modeli alan-alan doğrulama."""
    orders = await adapter_with_mock_client.fetch_orders(
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )
    await adapter_with_mock_client.close()

    assert len(orders) == 4

    o1 = orders[0]
    assert o1.external_id == "TY-2026-001"
    assert o1.customer_id == 1
    assert o1.platform_connection_id == 10
    assert o1.order_date.tzinfo is not None  # UTC olmalı

    pkg = o1.packages[0]
    assert pkg.external_id == "5001"
    assert pkg.status == PackageStatus.DELIVERED
    assert pkg.package_service_fee == DEFAULT_PACKAGE_SERVICE_FEE

    item = pkg.items[0]
    assert item.external_id == "1001"
    assert item.barcode == "ANON-BAR-001"
    assert item.product_id == "90001"
    assert item.quantity == 1
    assert item.unit_sale_price == Decimal("100.0")
    assert item.vat_rate == Decimal("0.20")  # 20 → 0.20 dönüşümü
    assert item.commission_rate == Decimal("0.18")
    assert item.campaign_discount == Decimal("0")
    assert item.cogs == Decimal("0")  # adapter COGS doldurmaz; müşteri yüklemesi


def test_status_mapping_covers_all_trendyol_statuses() -> None:
    """Trendyol'un 10 statüsü + bilinmeyen + boş için map doğru."""
    assert _map_status("Created") == PackageStatus.PENDING
    assert _map_status("Picking") == PackageStatus.PENDING
    assert _map_status("Invoiced") == PackageStatus.PENDING
    assert _map_status("Repack") == PackageStatus.PENDING
    assert _map_status("Shipped") == PackageStatus.SHIPPED
    assert _map_status("Delivered") == PackageStatus.DELIVERED
    assert _map_status("Cancelled") == PackageStatus.CANCELLED
    assert _map_status("UnDelivered") == PackageStatus.CANCELLED
    assert _map_status("UnSupplied") == PackageStatus.CANCELLED
    assert _map_status("Returned") == PackageStatus.RETURNED
    # Güvenli default'lar:
    assert _map_status("BrandNewStatus") == PackageStatus.PENDING
    assert _map_status(None) == PackageStatus.PENDING
    assert _map_status("") == PackageStatus.PENDING


async def test_order_with_multiple_packages_groups_lines(
    adapter_with_mock_client: TrendyolAdapter,
) -> None:
    """Aynı orderNumber'da farklı shipmentPackageId'ler ayrı paketlere düşmeli."""
    orders = await adapter_with_mock_client.fetch_orders(
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )
    await adapter_with_mock_client.close()

    o4 = orders[3]
    assert o4.external_id == "TY-2026-004"
    assert len(o4.packages) == 2

    statuses = {pkg.status for pkg in o4.packages}
    assert statuses == {PackageStatus.DELIVERED, PackageStatus.RETURNED}


async def test_discount_and_vat_rate_aggregation(
    adapter_with_mock_client: TrendyolAdapter,
) -> None:
    """Order 3 (Returned): discount=5, vatBaseAmount=10 → vat_rate=0.10, campaign=5.00"""
    orders = await adapter_with_mock_client.fetch_orders(
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )
    await adapter_with_mock_client.close()

    item = orders[2].packages[0].items[0]
    assert item.campaign_discount == Decimal("5.0")
    assert item.vat_rate == Decimal("0.10")
    assert item.quantity == 2


async def test_adapter_to_profit_engine_smoke(
    adapter_with_mock_client: TrendyolAdapter,
) -> None:
    """
    End-to-end smoke test: Trendyol fixture → adapter → calculate_order_profit.

    Order 1 (Delivered, 100 TL, %18 komisyon, %20 KDV, COGS=0):
        commission   = 100 × 0.18         = 18.00
        sale_vat     = 100 × 0.20 / 1.20  = 16.67
        total_cogs   = 0.00 (henüz yüklenmedi)
        item_net     = 100 - 18 - 16.67   = 65.33
        package_net  = 65.33 - 13.19 hizmet = 52.14
    """
    orders = await adapter_with_mock_client.fetch_orders(
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )
    await adapter_with_mock_client.close()

    r = calculate_order_profit(orders[0])
    assert r.gross_revenue == Decimal("100.00")
    assert r.commission == Decimal("18.00")
    assert r.sale_vat == Decimal("16.67")
    assert r.total_cogs == Decimal("0.00")
    assert r.service_fee == Decimal("13.19")
    assert r.net_profit == Decimal("52.14")
    assert r.is_realized is True
