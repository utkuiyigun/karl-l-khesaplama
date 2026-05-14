"""
Net kâr hesaplama motoru.

⚠️ PLATFORM-BAĞIMSIZ. Bu dosyada 'trendyol', 'shopify', 'platform' kelimesi GEÇEMEZ.
⚠️ Sadece app.adapters.base.types'tan import edebilir.
⚠️ TEST-FIRST. Önce tests/unit/test_profit.py yazılır, sonra burası doldurulur.

Matematiksel spec: docs/HESAPLAMA_MOTORU.md

Yuvarlama:
- Intermediate hesaplar tam Decimal precision'da tutulur (kayıp olmasın)
- ProfitResult'a girerken 2 hane'ye yuvarlanır (ROUND_HALF_UP)
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.adapters.base.types import Order, OrderItem, PackageStatus, ShipmentPackage

TWO_DP = Decimal("0.01")
ZERO = Decimal("0")


def _q(value: Decimal) -> Decimal:
    """Decimal'i 2 hane'ye yuvarla (half-up)."""
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


@dataclass
class ProfitResult:
    """Bir kalem, paket veya siparişin kâr hesabı detayı."""

    gross_revenue: Decimal       # Brüt gelir
    commission: Decimal          # Komisyon
    sale_vat: Decimal            # Satış KDV'si
    service_fee: Decimal         # Platform hizmet bedeli (kalem seviyesinde 0)
    shipping_cost: Decimal       # Kargo (kalem seviyesinde 0)
    total_cogs: Decimal          # Toplam alış maliyeti
    net_profit: Decimal          # NET KÂR (statü düzeltmesi uygulanmış)
    is_realized: bool            # True: tahsil edildi (Delivered/Shipped/Returned)


def calculate_item_profit(item: OrderItem) -> ProfitResult:
    """
    Tek bir kalem için kâr hesabı.

    HESAPLAMA §2.1. Paket hizmet bedeli ve kargo HARİÇ — bunlar paket
    seviyesinde eklenir. service_fee ve shipping_cost burada 0.00 döner.
    """
    effective_quantity = Decimal(item.quantity - item.return_quantity)

    gross_revenue = item.unit_sale_price * effective_quantity
    net_sale = gross_revenue - item.campaign_discount
    commission = net_sale * item.commission_rate
    sale_vat = net_sale * item.vat_rate / (Decimal("1") + item.vat_rate)
    total_cogs = item.cogs * effective_quantity

    item_net = net_sale - commission - sale_vat - total_cogs

    return ProfitResult(
        gross_revenue=_q(gross_revenue),
        commission=_q(commission),
        sale_vat=_q(sale_vat),
        service_fee=Decimal("0.00"),
        shipping_cost=Decimal("0.00"),
        total_cogs=_q(total_cogs),
        net_profit=_q(item_net),
        is_realized=True,  # kalem seviyesinde statü yok; paket override eder
    )


def calculate_package_profit(package: ShipmentPackage) -> ProfitResult:
    """
    Paket bazında net kâr (HESAPLAMA §2.2 + §2.3).

    Statüye göre düzeltme:
    - Cancelled  → net_profit = 0 (sipariş hiç gerçekleşmedi)
    - Returned   → net_profit = -(service_fee + shipping_cost) (komisyon iade,
                   COGS depoya döner, ama hizmet bedeli ve kargo zararı kalır)
    - Delivered / Shipped → raw_net, is_realized=True
    - Pending             → raw_net, is_realized=False
    """
    item_results = [calculate_item_profit(item) for item in package.items]

    gross_revenue = sum((r.gross_revenue for r in item_results), ZERO)
    commission = sum((r.commission for r in item_results), ZERO)
    sale_vat = sum((r.sale_vat for r in item_results), ZERO)
    total_cogs = sum((r.total_cogs for r in item_results), ZERO)
    items_net = sum((r.net_profit for r in item_results), ZERO)

    raw_net = items_net - package.package_service_fee - package.shipping_cost

    if package.status == PackageStatus.CANCELLED:
        adjusted_net = ZERO
        is_realized = False
    elif package.status == PackageStatus.RETURNED:
        adjusted_net = -package.package_service_fee - package.shipping_cost
        is_realized = True  # iade gerçekleşti, sonuç kesin
    elif package.status in (PackageStatus.DELIVERED, PackageStatus.SHIPPED):
        adjusted_net = raw_net
        is_realized = True
    else:  # PENDING
        adjusted_net = raw_net
        is_realized = False

    return ProfitResult(
        gross_revenue=_q(gross_revenue),
        commission=_q(commission),
        sale_vat=_q(sale_vat),
        service_fee=_q(package.package_service_fee),
        shipping_cost=_q(package.shipping_cost),
        total_cogs=_q(total_cogs),
        net_profit=_q(adjusted_net),
        is_realized=is_realized,
    )


def calculate_order_profit(order: Order) -> ProfitResult:
    """
    Tüm sipariş için toplam net kâr — paketler birleşik (HESAPLAMA §2.4).

    is_realized: tüm paketler realized ise True. Boş paket listesinde False.
    """
    package_results = [calculate_package_profit(pkg) for pkg in order.packages]

    return ProfitResult(
        gross_revenue=_q(sum((r.gross_revenue for r in package_results), ZERO)),
        commission=_q(sum((r.commission for r in package_results), ZERO)),
        sale_vat=_q(sum((r.sale_vat for r in package_results), ZERO)),
        service_fee=_q(sum((r.service_fee for r in package_results), ZERO)),
        shipping_cost=_q(sum((r.shipping_cost for r in package_results), ZERO)),
        total_cogs=_q(sum((r.total_cogs for r in package_results), ZERO)),
        net_profit=_q(sum((r.net_profit for r in package_results), ZERO)),
        is_realized=all(r.is_realized for r in package_results) if package_results else False,
    )
