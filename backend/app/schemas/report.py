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


class OrderDetail(OrderSummary):
    """Detay endpoint'inde paketler de gelir."""

    packages: list[ShipmentPackageRead]


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
