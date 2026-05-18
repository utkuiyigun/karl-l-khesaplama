"""
PLATFORM-BAĞIMSIZ İÇ VERİ TİPLERİ.

Bu dosyadaki tipler Trendyol, Shopify veya başka herhangi bir platformu BİLMEZ.
Hesaplama motoru sadece bu tipleri görür.

Adaptörler (trendyol/, shopify/) kendi ham JSON'larını bu tiplere dönüştürür.

KURAL: Bu dosyada platform-spesifik bir alan veya enum DEĞERİ olamaz.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class PackageStatus(str, Enum):
    """Platform-agnostik paket statüleri.
    
    Her adaptör kendi statüsünü bu enum'a map eder.
    """
    PENDING = "pending"          # Yeni, hazırlanıyor
    SHIPPED = "shipped"          # Kargoya verildi
    DELIVERED = "delivered"      # Teslim edildi
    CANCELLED = "cancelled"      # İptal
    RETURNED = "returned"        # İade


@dataclass
class OrderItem:
    """Sipariş kalemi - platform-bağımsız."""
    external_id: str             # Adaptörün verdiği unique ID
    product_id: str | None       # İç product ID (FK)
    barcode: str
    quantity: int
    unit_sale_price: Decimal     # KDV dahil birim satış fiyatı
    vat_rate: Decimal            # 0.10, 0.20 gibi
    commission_rate: Decimal     # Kategori komisyon oranı (KDV dahil)
    campaign_discount: Decimal = Decimal("0")  # Kalem başına toplam indirim
    return_quantity: int = 0
    cogs: Decimal = Decimal("0")  # Birim alış maliyeti, COGS yüklemesinden gelir


@dataclass
class ShipmentPackage:
    """Sipariş paketi - bir sipariş birden fazla pakete bölünebilir."""
    external_id: str
    status: PackageStatus
    items: list[OrderItem]
    package_service_fee: Decimal = Decimal("0")  # Platform hizmet bedeli (paket başı)
    shipping_cost: Decimal = Decimal("0")        # Kargo maliyeti


@dataclass
class Order:
    """Üst seviye sipariş."""
    external_id: str             # Trendyol'da orderNumber
    order_date: datetime
    customer_id: int             # İç müşteri ID
    platform_connection_id: int
    packages: list[ShipmentPackage] = field(default_factory=list)
    raw_data: dict | None = None  # ham platform response — debug/rapor için


@dataclass
class CustomerProfile:
    """
    Hesaplama motorunun müşteriye özgü vergi/maliyet bilgisini görmesi için
    platform-agnostik profil. DB Customer modeli'nden servis katmanında türetilir.

    Default değerler 'Senaryo A-E' davranışını korur (stopaj yok, KDV gider sayılır).
    """
    stopaj_rate: Decimal = field(default_factory=lambda: Decimal("0"))
    is_vat_registered: bool = True
    default_shipping_cost: Decimal = field(default_factory=lambda: Decimal("0"))
