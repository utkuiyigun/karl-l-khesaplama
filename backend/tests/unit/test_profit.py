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
from decimal import Decimal

import pytest

from app.adapters.base.types import OrderItem, PackageStatus, ShipmentPackage
from app.calculators.profit import calculate_item_profit, calculate_package_profit


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

    Input:
        unit_sale_price = 100 TL (KDV %20 dahil)
        quantity = 1, return = 0
        commission_rate = 0.18
        vat_rate = 0.20
        cogs = 40 TL

    Hesap (HESAPLAMA §2.1):
        gross_revenue = 100 × 1               = 100.00
        net_sale      = 100 − 0 (kampanya)    = 100.00
        commission    = 100 × 0.18            =  18.00
        sale_vat      = 100 × 0.20 / 1.20     =  16.67  (16.6666... yuvarlandı)
        total_cogs    = 40 × 1                =  40.00
        item_net      = 100 − 18 − 16.67 − 40 =  25.33
    """
    r = calculate_item_profit(simple_delivered_item)

    assert r.gross_revenue == Decimal("100.00")
    assert r.commission == Decimal("18.00")
    assert r.sale_vat == Decimal("16.67")
    assert r.total_cogs == Decimal("40.00")
    assert r.service_fee == Decimal("0.00"), "Kalem seviyesinde paket bedeli olmamalı"
    assert r.shipping_cost == Decimal("0.00"), "Kalem seviyesinde kargo olmamalı"
    assert r.net_profit == Decimal("25.33")


def test_senaryo_a_basit_teslim_package(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo A — PAKET seviyesi (HESAPLAMA §2.2).

    Aynı kalem + 13.19 TL hizmet bedeli + 0 TL kargo + Delivered:
        package_net = 25.33 − 13.19 − 0 = 12.14
    """
    package = ShipmentPackage(
        external_id="pkg-1",
        status=PackageStatus.DELIVERED,
        items=[simple_delivered_item],
        package_service_fee=Decimal("13.19"),
        shipping_cost=Decimal("0"),
    )
    r = calculate_package_profit(package)

    assert r.gross_revenue == Decimal("100.00")
    assert r.commission == Decimal("18.00")
    assert r.sale_vat == Decimal("16.67")
    assert r.service_fee == Decimal("13.19")
    assert r.shipping_cost == Decimal("0.00")
    assert r.total_cogs == Decimal("40.00")
    assert r.net_profit == Decimal("12.14")
    assert r.is_realized is True


@pytest.mark.skip(reason="TODO[2.2]: kısmi iade")
def test_senaryo_b_kismi_iade() -> None:
    pass


@pytest.mark.skip(reason="TODO[2.2]: tam iptal")
def test_senaryo_c_tam_iptal() -> None:
    pass


@pytest.mark.skip(reason="TODO[2.2]: kampanya indirimi")
def test_senaryo_d_kampanya_indirimi() -> None:
    pass


@pytest.mark.skip(reason="TODO[2.2]: çoklu paket karışık statü")
def test_senaryo_e_coklu_paket_karisik_statu() -> None:
    pass


@pytest.mark.skip(reason="TODO[2.3]: KDV mükellef değil")
def test_senaryo_f_kdv_mukellef_degil() -> None:
    pass


@pytest.mark.skip(reason="TODO[2.3]: stopajlı")
def test_senaryo_g_stopajli() -> None:
    pass
