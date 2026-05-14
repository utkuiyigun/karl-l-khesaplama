"""
Raporlama servisi.

DB'deki Order/Package/OrderItem kayıtlarını platform-agnostik
DomainOrder modeline çevirip hesaplama motoru üzerinden net kâr üretir.

Bu sayede:
- COGS güncellenirse rapor anında yansır (cogs_snapshot kullanılır)
- Statü değişimi (sync sırasında upsert) tabloyu otomatik günceller
"""
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base.types import CustomerProfile, Order as DomainOrder, OrderItem as DomainOrderItem
from app.adapters.base.types import ShipmentPackage as DomainShipmentPackage
from app.calculators.profit import (
    ProfitResult,
    calculate_item_profit,
    calculate_order_profit,
)
from app.models.customer import Customer
from app.models.order import Order as OrderModel
from app.models.order_item import OrderItem as OrderItemModel


def model_to_domain_order(order_model: OrderModel) -> DomainOrder:
    """SQLAlchemy Order modelini hesaplama motorunun gördüğü DomainOrder'a çevirir."""
    packages = []
    for pkg in order_model.packages:
        items = [
            DomainOrderItem(
                external_id=item.external_id,
                product_id=str(item.product_id) if item.product_id is not None else None,
                barcode=item.barcode,
                quantity=item.quantity,
                unit_sale_price=item.unit_sale_price,
                vat_rate=item.vat_rate,
                commission_rate=item.commission_rate,
                campaign_discount=item.campaign_discount,
                return_quantity=item.return_quantity,
                cogs=item.cogs_snapshot,
            )
            for item in pkg.items
        ]
        packages.append(
            DomainShipmentPackage(
                external_id=pkg.external_id,
                status=pkg.status,
                items=items,
                package_service_fee=pkg.package_service_fee,
                shipping_cost=pkg.shipping_cost,
            )
        )

    return DomainOrder(
        external_id=order_model.external_id,
        order_date=order_model.order_date,
        customer_id=order_model.customer_id,
        platform_connection_id=order_model.platform_connection_id,
        packages=packages,
    )


def customer_to_profile(customer: Customer) -> CustomerProfile:
    """DB Customer'dan hesap motorunun ihtiyacı olan profile'ı türetir."""
    return CustomerProfile(
        stopaj_rate=customer.stopaj_rate,
        is_vat_registered=customer.is_vat_registered,
        default_shipping_cost=customer.default_shipping_cost,
    )


async def list_orders_with_profit(
    session: AsyncSession,
    customer_id: int,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[tuple[OrderModel, ProfitResult]], int]:
    """Sipariş listesi: her satırda hem ham model hem hesaplanmış kâr.

    ADR-008: customer_id filtresi ZORUNLU (tenant izolasyonu).
    """
    customer = await session.get(Customer, customer_id)
    if customer is None:
        return [], 0

    profile = customer_to_profile(customer)

    total = (
        await session.execute(
            select(func.count(OrderModel.id)).where(OrderModel.customer_id == customer_id)
        )
    ).scalar_one()

    orders = (
        await session.execute(
            select(OrderModel)
            .where(OrderModel.customer_id == customer_id)
            .order_by(OrderModel.order_date.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    rows: list[tuple[OrderModel, ProfitResult]] = []
    for o in orders:
        domain = model_to_domain_order(o)
        rows.append((o, calculate_order_profit(domain, profile=profile)))
    return rows, total


async def get_order_with_profit(
    session: AsyncSession, customer_id: int, order_id: int
) -> tuple[OrderModel, ProfitResult] | None:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        return None

    order = await session.get(OrderModel, order_id)
    if order is None or order.customer_id != customer_id:
        return None

    profile = customer_to_profile(customer)
    domain = model_to_domain_order(order)
    return order, calculate_order_profit(domain, profile=profile)


async def product_profitability(
    session: AsyncSession, customer_id: int
) -> list[dict]:
    """Ürün bazlı kârlılık: barcode başına toplam satılan adet, brüt gelir, net kâr.

    OrderItem'ları barcode'a göre grupla → her grup için item kâr hesabı yap → topla.
    İade edilen miktarlar effective_quantity üzerinden zaten düşülmüş.
    """
    customer = await session.get(Customer, customer_id)
    if customer is None:
        return []
    _ = customer_to_profile(customer)  # ileride stopaj/KDV product seviyesinde uygulanırsa

    items = (
        await session.execute(
            select(OrderItemModel).where(OrderItemModel.customer_id == customer_id)
        )
    ).scalars().all()

    by_barcode: dict[str, dict] = {}
    for item in items:
        domain_item = DomainOrderItem(
            external_id=item.external_id,
            product_id=str(item.product_id) if item.product_id is not None else None,
            barcode=item.barcode,
            quantity=item.quantity,
            unit_sale_price=item.unit_sale_price,
            vat_rate=item.vat_rate,
            commission_rate=item.commission_rate,
            campaign_discount=item.campaign_discount,
            return_quantity=item.return_quantity,
            cogs=item.cogs_snapshot,
        )
        result = calculate_item_profit(domain_item)
        bucket = by_barcode.setdefault(
            item.barcode,
            {
                "barcode": item.barcode,
                "units_sold": 0,
                "units_returned": 0,
                "gross_revenue": Decimal("0"),
                "commission": Decimal("0"),
                "total_cogs": Decimal("0"),
                "item_net_profit": Decimal("0"),
            },
        )
        bucket["units_sold"] += item.quantity - item.return_quantity
        bucket["units_returned"] += item.return_quantity
        bucket["gross_revenue"] += result.gross_revenue
        bucket["commission"] += result.commission
        bucket["total_cogs"] += result.total_cogs
        bucket["item_net_profit"] += result.net_profit

    return sorted(by_barcode.values(), key=lambda r: r["item_net_profit"], reverse=True)


def simulate_campaign(
    items: Sequence[OrderItemModel],
    discount_pct: Decimal,
    volume_uplift_pct: Decimal = Decimal("0"),
) -> dict:
    """
    HESAPLAMA §5. Geçmiş kalemler üzerinden 'eğer %X indirim yapsaydık' sorusu.

    discount_pct: 0.20 = %20 indirim
    volume_uplift_pct: 0.10 = %10 hacim artışı varsayımı
    """
    base_net = Decimal("0")
    sim_net = Decimal("0")

    for item in items:
        # Baseline: mevcut COGS snapshot ile, mevcut fiyatla
        base_item = DomainOrderItem(
            external_id=item.external_id,
            product_id=None,
            barcode=item.barcode,
            quantity=item.quantity,
            unit_sale_price=item.unit_sale_price,
            vat_rate=item.vat_rate,
            commission_rate=item.commission_rate,
            campaign_discount=item.campaign_discount,
            return_quantity=item.return_quantity,
            cogs=item.cogs_snapshot,
        )
        base_net += calculate_item_profit(base_item).net_profit

        # Simüle: fiyat × (1 - discount), miktar × (1 + uplift)
        new_price = item.unit_sale_price * (Decimal("1") - discount_pct)
        new_qty = int(item.quantity * (Decimal("1") + volume_uplift_pct))
        sim_item = DomainOrderItem(
            external_id=item.external_id,
            product_id=None,
            barcode=item.barcode,
            quantity=new_qty,
            unit_sale_price=new_price,
            vat_rate=item.vat_rate,
            commission_rate=item.commission_rate,
            campaign_discount=Decimal("0"),
            return_quantity=item.return_quantity,
            cogs=item.cogs_snapshot,
        )
        sim_net += calculate_item_profit(sim_item).net_profit

    return {
        "base_net_profit": base_net,
        "simulated_net_profit": sim_net,
        "delta": sim_net - base_net,
        "discount_pct": discount_pct,
        "volume_uplift_pct": volume_uplift_pct,
    }
