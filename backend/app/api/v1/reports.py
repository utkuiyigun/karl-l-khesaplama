"""
Raporlama endpoint'leri.

URL pattern: /api/v1/customers/{customer_id}/...

Bağımlılık: app.services.reports — hesap motorunu üzerinden geçer.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.calculators.profit import ProfitResult
from app.db.session import get_db
from app.models.customer import Customer
from app.models.order import Order as OrderModel
from app.models.order_item import OrderItem as OrderItemModel
from app.schemas.common import Page
from app.schemas.report import (
    OrderDetail,
    OrderItemRead,
    OrderSummary,
    ProductProfitabilityRow,
    ProfitBreakdown,
    ShipmentPackageRead,
    SimulationRequest,
    SimulationResponse,
)
from app.services.reports import (
    get_order_with_profit,
    list_orders_with_profit,
    product_profitability,
    simulate_campaign,
)

router = APIRouter(prefix="/customers/{customer_id}", tags=["reports"])


def _profit_to_schema(p: ProfitResult) -> ProfitBreakdown:
    return ProfitBreakdown(
        gross_revenue=p.gross_revenue,
        commission=p.commission,
        sale_vat=p.sale_vat,
        service_fee=p.service_fee,
        shipping_cost=p.shipping_cost,
        total_cogs=p.total_cogs,
        stopaj=p.stopaj,
        net_profit=p.net_profit,
        is_realized=p.is_realized,
    )


@router.get("/orders", response_model=Page[OrderSummary])
async def list_orders(
    customer_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[OrderSummary]:
    rows, total = await list_orders_with_profit(db, customer_id, limit, offset)
    items = [
        OrderSummary(
            id=order.id,
            external_id=order.external_id,
            order_date=order.order_date,
            profit=_profit_to_schema(profit),
        )
        for order, profit in rows
    ]
    return Page[OrderSummary](items=items, total=total, limit=limit, offset=offset)


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order(
    customer_id: int,
    order_id: int,
    db: AsyncSession = Depends(get_db),
) -> OrderDetail:
    result = await get_order_with_profit(db, customer_id, order_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    order, profit = result
    return OrderDetail(
        id=order.id,
        external_id=order.external_id,
        order_date=order.order_date,
        profit=_profit_to_schema(profit),
        packages=[
            ShipmentPackageRead(
                id=pkg.id,
                external_id=pkg.external_id,
                status=pkg.status.value,
                raw_status=pkg.raw_status,
                package_service_fee=pkg.package_service_fee,
                shipping_cost=pkg.shipping_cost,
                items=[OrderItemRead.model_validate(item) for item in pkg.items],
            )
            for pkg in order.packages
        ],
    )


@router.get("/products/profitability", response_model=list[ProductProfitabilityRow])
async def product_profitability_report(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ProductProfitabilityRow]:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    rows = await product_profitability(db, customer_id)
    return [ProductProfitabilityRow(**r) for r in rows]


@router.post("/simulations", response_model=SimulationResponse)
async def simulate(
    customer_id: int,
    payload: SimulationRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """Geçmiş kalemler üzerinden 'şu indirim yapılsaydı' simülasyonu."""
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    items = (
        await db.execute(
            select(OrderItemModel).where(OrderItemModel.customer_id == customer_id)
        )
    ).scalars().all()

    if not items:
        return SimulationResponse(
            base_net_profit=Decimal("0"),
            simulated_net_profit=Decimal("0"),
            delta=Decimal("0"),
            discount_pct=payload.discount_pct,
            volume_uplift_pct=payload.volume_uplift_pct,
        )

    result = simulate_campaign(
        items,
        discount_pct=payload.discount_pct,
        volume_uplift_pct=payload.volume_uplift_pct,
    )
    return SimulationResponse(**result)
