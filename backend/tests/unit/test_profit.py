"""
Hesaplama motoru testleri.

⚠️ TEST-FIRST: Bu dosyadaki testler, app/calculators/profit.py'den ÖNCE yazılır.
⚠️ Hedef: %100 coverage on app/calculators/

Senaryo listesi: docs/HESAPLAMA_MOTORU.md §8

TODO[claude-code]:
- Her senaryo (A-G) için ayrı test fonksiyonu
- Fixture'ları tests/fixtures/scenarios/*.json
- pytest.mark.parametrize ile senaryoları döngüye al
"""
from decimal import Decimal

import pytest

from app.adapters.base.types import OrderItem, PackageStatus, ShipmentPackage


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


@pytest.mark.skip(reason="TODO[claude-code]: implement after writing profit.calculate_item_profit")
def test_senaryo_a_basit_teslim(simple_delivered_item: OrderItem) -> None:
    """
    Senaryo A: 100 TL satış, %18 komisyon, KDV %20, 40 TL COGS.
    
    Beklenen net kâr hesabını docs/HESAPLAMA_MOTORU.md'den manuel hesapla,
    burada assertion olarak yaz.
    """
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_b_kismi_iade() -> None:
    """Senaryo B: 2 adet ürünün 1'i iade edildi."""
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_c_tam_iptal() -> None:
    """Senaryo C: Cancelled → net etki 0."""
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_d_kampanya_indirimi() -> None:
    """Senaryo D: Komisyon indirimli fiyat üzerinden hesaplanmalı."""
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_e_coklu_paket_karisik_statu() -> None:
    """Senaryo E: 2 paket, biri Delivered biri Returned."""
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_f_kdv_mukellef_degil() -> None:
    """Senaryo F: KDV mahsuplaşması yok, tüm KDV gider."""
    pass


@pytest.mark.skip(reason="TODO[claude-code]")
def test_senaryo_g_stopajli() -> None:
    """Senaryo G: %5 stopaj net kârdan düşer."""
    pass
