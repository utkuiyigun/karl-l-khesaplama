"""
OrderItem — sipariş kalemi.

cogs_snapshot: hesap yapıldığı andaki Product.cogs değerinin kopyası. COGS
müşteri tarafından değiştirilirse eski siparişlerin kâr hesabı bozulmasın
diye tarihsel doğruluk için kalem üzerine kopyalanır.
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(primary_key=True)

    package_id: Mapped[int] = mapped_column(
        ForeignKey("shipment_package.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    quantity: Mapped[int] = mapped_column(nullable=False)
    return_quantity: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)

    unit_sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    campaign_discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    cogs_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
