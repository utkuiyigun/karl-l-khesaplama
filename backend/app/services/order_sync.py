"""
Sipariş senkronizasyon servisi.

İş akışı (TRENDYOL_API_NOTLAR §8):
1. Aktif bağlantıyı al
2. PlatformConnection.last_sync_at ile şimdi arası tarih aralığı (1 saat overlap buffer)
3. Adapter üzerinden siparişleri çek
4. DB'ye idempotent upsert (var olan kayıt güncellenir)
5. last_sync_at'ı now() olarak işaretle

Idempotency: (platform_connection_id, external_id) unique → INSERT ON CONFLICT yerine
SELECT-then-INSERT/UPDATE pattern. Order güncellenirken paketleri+kalemleri
silip yeniden yaz (CASCADE) — basit ve doğru, hesap sonuçları snapshot'lı.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base.types import Order as DomainOrder
from app.adapters.trendyol.adapter import TrendyolAdapter
from app.core.security import decrypt_secret
from app.db.session import AsyncSessionLocal
from app.models.order import Order as OrderModel
from app.models.order_item import OrderItem as OrderItemModel
from app.models.platform_connection import PlatformConnection
from app.models.product import Product
from app.models.shipment_package import ShipmentPackage as ShipmentPackageModel

OVERLAP_BUFFER = timedelta(hours=1)


async def find_active_connection_ids() -> list[int]:
    """Senkron edilecek tüm aktif bağlantıların ID'leri."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PlatformConnection.id).where(PlatformConnection.is_active.is_(True))
        )
        return [row[0] for row in result.all()]


def _build_adapter(conn: PlatformConnection) -> TrendyolAdapter:
    """PlatformConnection'a göre platform-spesifik adapter oluştur.

    Şu an sadece Trendyol; Shopify Faz 2'de eklenecek.
    """
    if conn.platform == "trendyol":
        return TrendyolAdapter(
            api_key=decrypt_secret(conn.api_key_encrypted),
            api_secret=decrypt_secret(conn.api_secret_encrypted),
            seller_id=conn.seller_id,
            customer_id=conn.customer_id,
            platform_connection_id=conn.id,
        )
    raise ValueError(f"Unsupported platform: {conn.platform}")


def _sync_window(conn: PlatformConnection) -> tuple[datetime, datetime]:
    """[last_sync − 1h, now]; ilk sync ise sync_start_date'ten başla."""
    end = datetime.now(timezone.utc)
    base = conn.last_sync_at or conn.sync_start_date
    start = base - OVERLAP_BUFFER
    return start, end


async def sync_connection_orders(connection_id: int) -> dict[str, Any]:
    """
    Tek bir bağlantı için Trendyol'dan siparişleri çek + DB'ye yaz.

    Worker (Celery task) tarafından çağrılır. Kendi session'ını açar.
    """
    async with AsyncSessionLocal() as session:
        conn = await session.get(PlatformConnection, connection_id)
        if conn is None or not conn.is_active:
            return {"skipped": "inactive_or_missing", "connection_id": connection_id}

        adapter = _build_adapter(conn)
        start, end = _sync_window(conn)

        try:
            orders = await adapter.fetch_orders(start_date=start, end_date=end)
        finally:
            await adapter.close()

        processed = 0
        for order in orders:
            await _upsert_order(session, order)
            processed += 1

        conn.last_sync_at = end
        await session.commit()

        return {
            "connection_id": connection_id,
            "customer_id": conn.customer_id,
            "orders_processed": processed,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
        }


async def _upsert_order(session: AsyncSession, domain_order: DomainOrder) -> None:
    """Bir sipariş için: order kaydı (insert ya da update) + paket/kalemleri yeniden yaz.

    raw_data MVP'de boş dict; ileride adapter raw JSON'u attach edecek.
    """
    existing_q = await session.execute(
        select(OrderModel).where(
            OrderModel.platform_connection_id == domain_order.platform_connection_id,
            OrderModel.external_id == domain_order.external_id,
        )
    )
    existing = existing_q.scalar_one_or_none()

    if existing is None:
        order_row = OrderModel(
            customer_id=domain_order.customer_id,
            platform_connection_id=domain_order.platform_connection_id,
            external_id=domain_order.external_id,
            order_date=domain_order.order_date,
            raw_data={},
        )
        session.add(order_row)
        await session.flush()
    else:
        order_row = existing
        order_row.order_date = domain_order.order_date
        # raw_data güncellenmiyor şimdilik
        # Eski paketleri sil (CASCADE order_items'ı da siler)
        await session.execute(
            delete(ShipmentPackageModel).where(ShipmentPackageModel.order_id == order_row.id)
        )
        await session.flush()

    for pkg in domain_order.packages:
        pkg_row = ShipmentPackageModel(
            order_id=order_row.id,
            customer_id=domain_order.customer_id,
            external_id=pkg.external_id,
            status=pkg.status,
            raw_status=pkg.status.value,
            package_service_fee=pkg.package_service_fee,
            shipping_cost=pkg.shipping_cost,
        )
        session.add(pkg_row)
        await session.flush()

        for item in pkg.items:
            # COGS lookup: müşteri yüklediyse Product tablosundan al, yoksa 0
            product = (
                await session.execute(
                    select(Product).where(
                        Product.customer_id == domain_order.customer_id,
                        Product.barcode == item.barcode,
                    )
                )
            ).scalar_one_or_none()

            item_row = OrderItemModel(
                package_id=pkg_row.id,
                order_id=order_row.id,
                customer_id=domain_order.customer_id,
                product_id=product.id if product else None,
                external_id=item.external_id,
                barcode=item.barcode,
                quantity=item.quantity,
                return_quantity=item.return_quantity,
                unit_sale_price=item.unit_sale_price,
                vat_rate=item.vat_rate,
                commission_rate=item.commission_rate,
                campaign_discount=item.campaign_discount,
                cogs_snapshot=product.cogs if product else item.cogs,
            )
            session.add(item_row)
