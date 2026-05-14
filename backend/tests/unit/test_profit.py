"""
Hesaplama motoru testleri.

⚠️ TEST-FIRST: Bu dosyadaki testler, app/calculators/profit.py'den ÖNCE yazılır.
⚠️ Hedef: %100 coverage on app/calculators/

Senaryo listesi: docs/HESAPLAMA_MOTORU.md §8

Implementasyon stratejisi:
- inline Python dataclass'lar ile senaryo tanımlanır (tip güvenli, IDE-friendly)
- Beklenen sonuçlar yorumda hesap adımıyla birlikte yazılır
- Tüm para alanları Decimal; karşılaştırma tam değerle
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.adapters.base.types import (
    CustomerProfile,
    Order,
    OrderItem,
    PackageStatus,
    ShipmentPackage,
)
from app.calculators.profit import (
    calculate_item_profit,
    calculate_order_profit,
    calculate_package_profit,
)


# ---------------------------------------------------------------------------
# Senaryo A — Basit teslim
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_delivered_item() -> OrderItem:
    """Senaryo A baseline: basit teslim edilmiş kalem."""
    return OrderItem(
        external_id="item-1",
        product_id="1",
        barcode="1234567890",
        quantity=1,
        unit_sale_price=Decimal("100.00"),
        vat_rate=Decimal("0.20"),
        commission_rate=Decimal("0.18"),
        cogs=Decimal("40.00"),
    )


def test_senaryo_a_basit_teslim_item(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo A — KALEM seviyesi.

    100 TL × 1 adet, %18 komisyon, %20 KDV dahil, 40 TL COGS.
        gross_revenue = 100.00
        commission    = 100 × 0.18      = 18.00
        sale_vat      = 100 × 0.20/1.20 = 16.67
        total_cogs    = 40.00
        item_net      = 100 - 18 - 16.67 - 40 = 25.33
    """
    r = calculate_item_profit(simple_delivered_item)
    assert r.gross_revenue == Decimal("100.00")
    assert r.commission == Decimal("18.00")
    assert r.sale_vat == Decimal("16.67")
    assert r.total_cogs == Decimal("40.00")
    assert r.service_fee == Decimal("0.00")
    assert r.shipping_cost == Decimal("0.00")
    assert r.net_profit == Decimal("25.33")


def test_senaryo_a_basit_teslim_package(simple_delivered_item: OrderItem) -> None:
    """Senaryo A — PAKET: 25.33 - 13.19 hizmet - 0 kargo = 12.14"""
    package = ShipmentPackage(
        external_id="pkg-1",
        status=PackageStatus.DELIVERED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
        shipping_cost=Decimal("0"),
    )
    r = calculate_package_profit(package)
    assert r.net_profit == Decimal("12.14")
    assert r.is_realized is True


# ---------------------------------------------------------------------------
# Senaryo B — Kısmi iade (2 adet, 1'i iade)
# ---------------------------------------------------------------------------


def test_senaryo_b_kismi_iade() -> None:
    """
    Senaryo B — KISMİ İADE.

    2 adet ürün satıldı, 1'i iade. Kalan 1 adet için kâr hesaplanmalı.
        effective_quantity = 2 - 1 = 1
        Net rakamlar Senaryo A ile aynı: item_net=25.33, package_net=12.14
    """
    item = OrderItem(
        external_id="item-b",
        product_id="1",
        barcode="b",
        quantity=2,
        return_quantity=1,
        unit_sale_price=Decimal("100.00"),
        vat_rate=Decimal("0.20"),
        commission_rate=Decimal("0.18"),
        cogs=Decimal("40.00"),
    )
    item_r = calculate_item_profit(item)
    assert item_r.gross_revenue == Decimal("100.00")  # sadece 1 adet için
    assert item_r.commission == Decimal("18.00")
    assert item_r.total_cogs == Decimal("40.00")  # sadece 1 adet için
    assert item_r.net_profit == Decimal("25.33")

    package = ShipmentPackage(
        external_id="pkg-b",
        status=PackageStatus.DELIVERED,
        items=[item],
        package_service_fee=Decimal("13.19"),
    )
    pkg_r = calculate_package_profit(package)
    assert pkg_r.net_profit == Decimal("12.14")


# ---------------------------------------------------------------------------
# Senaryo C — Tam iptal
# ---------------------------------------------------------------------------


def test_senaryo_c_tam_iptal(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo C — TAM İPTAL.

    Aynı kalem + statü=Cancelled → net_profit=0, is_realized=False.
    Komisyon, hizmet bedeli vs. raporda ham kalabilir (referans için)
    ama net etki kesinlikle 0.
    """
    package = ShipmentPackage(
        external_id="pkg-c",
        status=PackageStatus.CANCELLED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
    )
    r = calculate_package_profit(package)
    assert r.net_profit == Decimal("0.00")
    assert r.is_realized is False


# ---------------------------------------------------------------------------
# Senaryo D — Kampanya indirimi (komisyon indirimli fiyat üzerinden)
# ---------------------------------------------------------------------------


def test_senaryo_d_kampanya_indirimi() -> None:
    """
    Senaryo D — KAMPANYA İNDİRİMİ.

    100 TL satış − 20 TL kampanya = 80 TL net satış.
    Komisyon ve KDV İNDİRİMLİ fiyat üzerinden hesaplanır (KRİTİK!).
        gross_revenue = 100 × 1                = 100.00
        net_sale      = 100 - 20               =  80.00
        commission    = 80 × 0.18              =  14.40
        sale_vat      = 80 × 0.20 / 1.20       =  13.33  (13.333... yuvarlandı)
        total_cogs    = 40.00
        item_net      = 80 - 14.40 - 13.33 - 40 = 12.27
    """
    item = OrderItem(
        external_id="item-d",
        product_id="1",
        barcode="d",
        quantity=1,
        unit_sale_price=Decimal("100.00"),
        vat_rate=Decimal("0.20"),
        commission_rate=Decimal("0.18"),
        campaign_discount=Decimal("20.00"),
        cogs=Decimal("40.00"),
    )
    r = calculate_item_profit(item)
    assert r.gross_revenue == Decimal("100.00")  # brüt etiket fiyatı
    assert r.commission == Decimal("14.40"), "Komisyon İNDİRİMLİ fiyat üzerinden olmalı"
    assert r.sale_vat == Decimal("13.33")
    assert r.total_cogs == Decimal("40.00")
    assert r.net_profit == Decimal("12.27")


# ---------------------------------------------------------------------------
# Senaryo E — Çoklu paket, karışık statü (Delivered + Returned)
# ---------------------------------------------------------------------------


def test_senaryo_e_coklu_paket_karisik_statu(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo E — ÇOKLU PAKET.

    1 sipariş, 2 paket aynı kalemle: P1 Delivered, P2 Returned.
        P1.net = 12.14  (Senaryo A)
        P2.net = -(13.19 + 0) = -13.19  (Returned: sadece hizmet+kargo zararı)
        order.net = 12.14 - 13.19 = -1.05
    """
    second_item = OrderItem(
        external_id="item-e2",
        product_id="1",
        barcode="e2",
        quantity=simple_delivered_item.quantity,
        unit_sale_price=simple_delivered_item.unit_sale_price,
        vat_rate=simple_delivered_item.vat_rate,
        commission_rate=simple_delivered_item.commission_rate,
        cogs=simple_delivered_item.cogs,
    )

    p1 = ShipmentPackage(
        external_id="pkg-e1",
        status=PackageStatus.DELIVERED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
    )
    p2 = ShipmentPackage(
        external_id="pkg-e2",
        status=PackageStatus.RETURNED,
        items=[second_item],
        package_service_fee=Decimal("13.19"),
    )

    p1_r = calculate_package_profit(p1)
    p2_r = calculate_package_profit(p2)
    assert p1_r.net_profit == Decimal("12.14")
    assert p2_r.net_profit == Decimal("-13.19")
    assert p2_r.is_realized is True  # iade gerçekleşti, sonuç kesin

    order = Order(
        external_id="ord-e",
        order_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
        customer_id=1,
        platform_connection_id=1,
        packages=[p1, p2],
    )
    o = calculate_order_profit(order)
    assert o.net_profit == Decimal("-1.05")
    assert o.is_realized is True  # her iki paket de realized


# ---------------------------------------------------------------------------
# Edge cases — coverage tamamlama
# ---------------------------------------------------------------------------


def test_pending_package_returns_raw_net_with_is_realized_false() -> None:
    """PENDING statüsünde paket hesabı raw net döner ama is_realized=False
    (Sipariş hazırlık aşamasında; tahsil edilmedi henüz)."""
    item = OrderItem(
        external_id="item-p",
        product_id=None,
        barcode="p",
        quantity=1,
        unit_sale_price=Decimal("100.00"),
        vat_rate=Decimal("0.20"),
        commission_rate=Decimal("0.18"),
        cogs=Decimal("40.00"),
    )
    package = ShipmentPackage(
        external_id="pkg-p",
        status=PackageStatus.PENDING,
        items=[item],
        package_service_fee=Decimal("13.19"),
    )
    r = calculate_package_profit(package)
    assert r.net_profit == Decimal("12.14")
    assert r.is_realized is False


def test_empty_order_is_not_realized() -> None:
    """Hiç paketi olmayan sipariş: tüm tutarlar 0, is_realized=False."""
    order = Order(
        external_id="ord-empty",
        order_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
        customer_id=1,
        platform_connection_id=1,
        packages=[],
    )
    r = calculate_order_profit(order)
    assert r.net_profit == Decimal("0.00")
    assert r.is_realized is False


# ---------------------------------------------------------------------------
# Senaryo G — Stopaj (customer profile ile)
# ---------------------------------------------------------------------------


def test_senaryo_g_stopajli(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo G — STOPAJ.

    Senaryo A baseline + stopaj_rate=0.05 → paket net'inden %5 stopaj kesilir.
        base_net = 12.14
        stopaj   = 12.14 × 0.05 = 0.607 → 0.61
        final    = 12.14 - 0.61          = 11.53
    """
    package = ShipmentPackage(
        external_id="pkg-g",
        status=PackageStatus.DELIVERED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
    )
    profile = CustomerProfile(stopaj_rate=Decimal("0.05"))
    r = calculate_package_profit(package, profile=profile)
    assert r.stopaj == Decimal("0.61")
    assert r.net_profit == Decimal("11.53")


def test_stopaj_not_applied_to_negative_net(simple_delivered_item: OrderItem) -> None:
    """Returned paket için adjusted_net negatif → stopaj uygulanmaz (zarara stopaj olmaz)."""
    package = ShipmentPackage(
        external_id="pkg-returned",
        status=PackageStatus.RETURNED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
    )
    profile = CustomerProfile(stopaj_rate=Decimal("0.05"))
    r = calculate_package_profit(package, profile=profile)
    assert r.stopaj == Decimal("0.00")
    assert r.net_profit == Decimal("-13.19")


def test_stopaj_propagates_to_order_total(simple_delivered_item: OrderItem) -> None:
    """calculate_order_profit profile'ı paketlere geçirir, order.stopaj = sum(pkg.stopaj)."""
    package = ShipmentPackage(
        external_id="pkg-ord-g",
        status=PackageStatus.DELIVERED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
    )
    order = Order(
        external_id="ord-g",
        order_date=datetime(2026, 5, 14, tzinfo=timezone.utc),
        customer_id=1,
        platform_connection_id=1,
        packages=[package],
    )
    profile = CustomerProfile(stopaj_rate=Decimal("0.05"))
    r = calculate_order_profit(order, profile=profile)
    assert r.stopaj == Decimal("0.61")
    assert r.net_profit == Decimal("11.53")


# ---------------------------------------------------------------------------
# Senaryo F — KDV mükellef değil
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "MVP basit KDV modu — HESAPLAMA §6'da 'MVP'de basit mod, gelişmiş ayar olarak işaretle' "
        "denildiği için KDV mahsuplaşması ileri faza bırakıldı. CustomerProfile.is_vat_registered "
        "alanı şimdilik referans için var; davranışı yok."
    )
)
def test_senaryo_f_kdv_mukellef_degil() -> None:
    pass
