"""
Raporlama endpoint'lerinin response schema'ları.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProfitBreakdown(BaseModel):
    gross_revenue: Decimal
    commission: Decimal
    sale_vat: Decimal
    service_fee: Decimal
    shipping_cost: Decimal
    total_cogs: Decimal
    stopaj: Decimal
    net_profit: Decimal
    is_realized: bool


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    barcode: str
    quantity: int
    return_quantity: int
    unit_sale_price: Decimal
    vat_rate: Decimal
    commission_rate: Decimal
    campaign_discount: Decimal
    cogs_snapshot: Decimal


class ShipmentPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    status: str
    raw_status: str
    package_service_fee: Decimal
    shipping_cost: Decimal
    items: list[OrderItemRead]


class OrderSummary(BaseModel):
    """List endpoint'inde tek bir satır."""

    id: int
    external_id: str
    order_date: datetime
    profit: ProfitBreakdown


class TrendyolBreakdown(BaseModel):
    """Trendyol'un sipariş seviyesinde döndürdüğü ham finansal alanlar.

    Sipariş detayında 'Trendyol Hesaplaşma' bölümünde göstermek için raw_data'dan
    çıkarılır. Kargo/ceza gibi alanlar /orders endpoint'inde GELMEZ —
    Trendyol'un finans Excel raporu'ndan gelir (sonraki Faz'da import edilebilir).
    """

    gross_amount: Decimal | None = None
    total_discount: Decimal | None = None
    seller_discount: Decimal | None = None
    ty_discount: Decimal | None = None
    total_price: Decimal | None = None  # indirim sonrası satıcının tahsil edeceği tutar
    cargo_provider: str | None = None
    cargo_tracking_number: str | None = None
    delivery_type: str | None = None


class OrderDetail(OrderSummary):
    """Detay endpoint'inde paketler de gelir."""

    packages: list[ShipmentPackageRead]
    trendyol_breakdown: TrendyolBreakdown | None = None


class ProductProfitabilityRow(BaseModel):
    barcode: str
    units_sold: int
    units_returned: int
    gross_revenue: Decimal
    commission: Decimal
    total_cogs: Decimal
    item_net_profit: Decimal


class SimulationRequest(BaseModel):
    discount_pct: Decimal = Field(ge=0, le=1, description="0.20 = %20 indirim")
    volume_uplift_pct: Decimal = Field(default=Decimal("0"), ge=0, le=10)


class SimulationResponse(BaseModel):
    base_net_profit: Decimal
    simulated_net_profit: Decimal
    delta: Decimal
    discount_pct: Decimal
    volume_uplift_pct: Decimal
