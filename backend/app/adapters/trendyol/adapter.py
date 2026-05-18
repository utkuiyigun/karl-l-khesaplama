"""
Trendyol adaptörü — ham Trendyol JSON'unu iç modele dönüştürür.

Sorumluluğu:
- HTTP'i client'a delege etmek (kendi HTTP koymaz)
- Ham JSON alanlarını platform-agnostik Order/ShipmentPackage/OrderItem'a map etmek
- Statü adlarını PackageStatus enum'una map etmek
- Para alanlarını Decimal'a güvenli çevirmek (float'tan kaçın)

⚠️ Hesaplama YAPMAZ — sadece dönüşüm. Net kâr motorunun işi (calculators/profit.py).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.adapters.base.adapter import MarketplaceAdapter
from app.adapters.base.types import (
    Order,
    OrderItem,
    PackageStatus,
    ShipmentPackage,
)
from app.adapters.trendyol.client import TrendyolClient

# HESAPLAMA §3: paket başına platform hizmet bedeli (sabit, MVP)
DEFAULT_PACKAGE_SERVICE_FEE = Decimal("13.19")

# Trendyol statüleri → iç enum
_STATUS_MAP: dict[str, PackageStatus] = {
    "Created": PackageStatus.PENDING,
    "Picking": PackageStatus.PENDING,
    "Invoiced": PackageStatus.PENDING,
    "Repack": PackageStatus.PENDING,
    "Shipped": PackageStatus.SHIPPED,
    "Delivered": PackageStatus.DELIVERED,
    "Cancelled": PackageStatus.CANCELLED,
    "UnDelivered": PackageStatus.CANCELLED,
    "UnSupplied": PackageStatus.CANCELLED,
    "Returned": PackageStatus.RETURNED,
}


def _map_status(raw: str | None) -> PackageStatus:
    """Bilinmeyen veya boş statü güvenli default: PENDING (henüz tamamlanmadı)."""
    if not raw:
        return PackageStatus.PENDING
    return _STATUS_MAP.get(raw, PackageStatus.PENDING)


def _to_decimal(value: Any) -> Decimal:
    """JSON float'unu Decimal'a güvenli çevir (str-via, IEEE 754 hatasını önler)."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _build_order_item(line: dict[str, Any]) -> OrderItem:
    # KDV: gerçek API'de `vatRate` (örn 20.0), eski test fixture'ında `vatBaseAmount`.
    vat_pct = _to_decimal(line.get("vatRate", line.get("vatBaseAmount", 0)))
    vat_rate = vat_pct / Decimal("100")

    # Komisyon: gerçek API'de `commission` (yüzde, 12 = %12).
    # Eski fixture (test) ile geriye dönük uyumluluk için `commissionRate` (oran) destekli.
    if "commission" in line:
        commission_rate = _to_decimal(line["commission"]) / Decimal("100")
    else:
        commission_rate = _to_decimal(line.get("commissionRate", 0))

    # Brüt birim fiyat: Trendyol'un `price` alanı ZATEN indirimli (örn 2070).
    # Brüt `amount` veya `lineGrossAmount` verir (örn 2300). Brütü tercih et,
    # indirimi `campaign_discount` olarak ayrı tut — hesap motoru net_sale = gross - discount
    # şeklinde işliyor (HESAPLAMA §2.1).
    quantity = int(line.get("quantity", 1))
    line_gross = _to_decimal(line.get("amount", line.get("lineGrossAmount", line.get("price", 0))))
    unit_sale_price = (
        line_gross / Decimal(quantity) if quantity > 0 else line_gross
    )

    # Toplam indirim: gerçek API'de lineTotalDiscount; eski fixture'da
    # discount + tyDiscount + merchantDiscount toplamı.
    if "lineTotalDiscount" in line:
        discount = _to_decimal(line["lineTotalDiscount"])
    else:
        discount = (
            _to_decimal(line.get("discount", 0))
            + _to_decimal(line.get("tyDiscount", 0))
            + _to_decimal(line.get("merchantDiscount", 0))
        )

    product_code = line.get("productCode")

    return OrderItem(
        external_id=str(line["id"]),
        product_id=str(product_code) if product_code is not None else None,
        barcode=str(line.get("barcode", "")),
        quantity=quantity,
        unit_sale_price=unit_sale_price,
        vat_rate=vat_rate,
        commission_rate=commission_rate,
        campaign_discount=discount,
        cogs=Decimal("0"),  # COGS müşteri yüklemesinden gelir
    )


def _build_packages(
    lines: list[dict[str, Any]],
    raw_order: dict[str, Any],
) -> list[ShipmentPackage]:
    """lines'ı shipmentPackageId'ye göre grupla. Gerçek Trendyol API'sinde
    shipmentPackageId sipariş seviyesinde; eski fixture'da line'da gelir.
    İkisini de destekle (line öncelikli, yoksa sipariş üst seviyesi)."""
    fallback_pkg_id = str(
        raw_order.get("shipmentPackageId", raw_order.get("id", "single"))
    )
    fallback_status = raw_order.get("shipmentPackageStatus", raw_order.get("status"))

    groups: dict[str, list[dict[str, Any]]] = {}
    for line in lines:
        pkg_id = str(line.get("shipmentPackageId", fallback_pkg_id))
        groups.setdefault(pkg_id, []).append(line)

    packages: list[ShipmentPackage] = []
    for pkg_id, group_lines in groups.items():
        raw_status = group_lines[0].get("orderLineItemStatusName") or fallback_status
        packages.append(
            ShipmentPackage(
                external_id=pkg_id,
                status=_map_status(raw_status),
                items=[_build_order_item(line) for line in group_lines],
                package_service_fee=DEFAULT_PACKAGE_SERVICE_FEE,
                shipping_cost=Decimal("0"),
            )
        )
    return packages


def _parse_order(
    raw: dict[str, Any],
    customer_id: int,
    platform_connection_id: int,
) -> Order:
    return Order(
        external_id=str(raw["orderNumber"]),
        order_date=datetime.fromtimestamp(raw["orderDate"] / 1000, tz=timezone.utc),
        customer_id=customer_id,
        platform_connection_id=platform_connection_id,
        packages=_build_packages(raw.get("lines", []), raw),
        raw_data=raw,  # detayda Trendyol Hesaplaşma Dökümü için ham JSON
    )


class TrendyolAdapter(MarketplaceAdapter):
    """Trendyol Marketplace API adaptörü.

    Bir müşterinin bir bağlantısı için context taşır (customer_id, connection_id).
    İçinde TrendyolClient HTTP işini yapar; bu sınıf sadece mapping.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        seller_id: str,
        customer_id: int,
        platform_connection_id: int,
        *,
        client: TrendyolClient | None = None,
    ):
        self.seller_id = seller_id
        self.customer_id = customer_id
        self.platform_connection_id = platform_connection_id
        self._client = client or TrendyolClient(api_key, api_secret, seller_id)

    async def close(self) -> None:
        await self._client.close()

    async def fetch_orders(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Order]:
        """Tek sayfa siparişleri çek + iç modele dönüştür.

        NOT: Pagination ve 14 günlük chunking sync worker (Faz 4) tarafında yapılır.
        Bu metot tek bir API çağrısının sonucunu döndürür.
        """
        response = await self._client.list_orders(
            start_date=start_date,
            end_date=end_date,
            page=0,
            size=200,
        )
        return [
            _parse_order(raw, self.customer_id, self.platform_connection_id)
            for raw in response.get("content", [])
        ]

    async def fetch_products(self) -> list[dict[str, Any]]:
        """Ürün listesi (COGS eşleştirmesi için). Faz 3.4'te implement edilecek."""
        raise NotImplementedError("TODO[3.4]: fetch_products endpoint'ini implement et")

    def get_platform_name(self) -> str:
        return "trendyol"
