"""
Fiyat simülatörü endpoint.

POST /api/v1/customers/{id}/price-simulator
Tek bir kalemin satış senaryosunu hesaplama motoru üzerinden geçirir.
Müşterinin stopaj_rate gibi profil bilgileri DB'den alınır.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base.types import (
    CustomerProfile,
    OrderItem as DomainOrderItem,
    PackageStatus,
    ShipmentPackage as DomainShipmentPackage,
)
from app.calculators.profit import calculate_package_profit
from app.db.session import get_db
from app.models.customer import Customer
from app.schemas.price_simulator import (
    PriceSimulatorRequest,
    PriceSimulatorResponse,
)

router = APIRouter(prefix="/customers/{customer_id}/price-simulator", tags=["simulator"])


@router.post("", response_model=PriceSimulatorResponse)
async def simulate_price(
    customer_id: int,
    payload: PriceSimulatorRequest,
    db: AsyncSession = Depends(get_db),
) -> PriceSimulatorResponse:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    item = DomainOrderItem(
        external_id="simulator",
        product_id=None,
        barcode="simulator",
        quantity=payload.quantity,
        unit_sale_price=payload.sale_price,
        vat_rate=payload.vat_rate,
        commission_rate=payload.commission_rate,
        campaign_discount=payload.campaign_discount,
        cogs=payload.cogs,
    )
    package = DomainShipmentPackage(
        external_id="simulator",
        status=PackageStatus.DELIVERED,
        items=[item],
        package_service_fee=payload.package_service_fee,
        shipping_cost=payload.shipping_cost,
    )
    profile = CustomerProfile(
        stopaj_rate=customer.stopaj_rate,
        is_vat_registered=customer.is_vat_registered,
    )
    r = calculate_package_profit(package, profile=profile)

    # Seller payout — Trendyol'un satıcıya yatırdığı tutar (Excel'deki "Net Tutar"):
    # gross - kampanya - komisyon - hizmet bedeli - kargo (KDV burada hâlâ dahil)
    seller_payout = (
        r.gross_revenue
        - payload.campaign_discount
        - r.commission
        - r.service_fee
        - r.shipping_cost
    )

    return PriceSimulatorResponse(
        gross_revenue=r.gross_revenue,
        campaign_discount=payload.campaign_discount,
        net_sale=r.gross_revenue - payload.campaign_discount,
        commission=r.commission,
        service_fee=r.service_fee,
        shipping_cost=r.shipping_cost,
        sale_vat=r.sale_vat,
        total_cogs=r.total_cogs,
        stopaj=r.stopaj,
        seller_payout=seller_payout,
        net_profit=r.net_profit,
    )
