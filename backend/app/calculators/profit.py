"""
Net kâr hesaplama motoru.

⚠️ PLATFORM-BAĞIMSIZ. Bu dosyada 'trendyol', 'shopify', 'platform' kelimesi GEÇEMEZ.
⚠️ Sadece app.adapters.base.types'tan import edebilir.
⚠️ TEST-FIRST. Önce tests/unit/test_profit.py yazılır, sonra burası doldurulur.

Matematiksel spec: docs/HESAPLAMA_MOTORU.md

Geliştirme sırası:
1. tests/fixtures/scenarios/ altına input+expected_output JSON'ları koy (Senaryo A-G)
2. tests/unit/test_profit.py — her senaryo için test yaz
3. Buradaki fonksiyonları kademeli implement et, tüm testler geçene kadar
"""
from dataclasses import dataclass
from decimal import Decimal

from app.adapters.base.types import Order, OrderItem, PackageStatus, ShipmentPackage


@dataclass
class ProfitResult:
    """Bir sipariş, paket veya kalemin kâr hesabı detayı."""
    gross_revenue: Decimal       # Brüt gelir
    commission: Decimal          # Komisyon
    sale_vat: Decimal            # Satış KDV'si
    service_fee: Decimal         # Platform hizmet bedeli
    shipping_cost: Decimal       # Kargo
    total_cogs: Decimal          # Toplam alış maliyeti
    net_profit: Decimal          # NET KÂR (en önemli)
    is_realized: bool            # Gerçekleşti mi (Delivered) yoksa pending mi


def calculate_item_profit(item: OrderItem) -> ProfitResult:
    """
    Tek bir kalem için kâr hesabı (paket bedeli ve kargo HARİÇ).
    Bunlar paket seviyesinde eklenir/düşülür.
    
    TODO[claude-code]: Implement.
    Bkz: docs/HESAPLAMA_MOTORU.md §2.1
    """
    raise NotImplementedError("test-first: önce testleri yaz")


def calculate_package_profit(package: ShipmentPackage) -> ProfitResult:
    """
    Paket bazında net kâr.
    Statüye göre düzeltme yapar (Cancelled→0, Returned→negatif, vs.).
    
    TODO[claude-code]: Implement.
    Bkz: docs/HESAPLAMA_MOTORU.md §2.2 ve §2.3
    """
    raise NotImplementedError("test-first: önce testleri yaz")


def calculate_order_profit(order: Order) -> ProfitResult:
    """
    Tüm sipariş için toplam net kâr (tüm paketler birleşik).
    
    TODO[claude-code]: Implement.
    Bkz: docs/HESAPLAMA_MOTORU.md §2.4
    """
    raise NotImplementedError("test-first: önce testleri yaz")
