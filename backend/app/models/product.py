"""
Product — müşterinin pazaryerindeki ürünü.

COGS (alış maliyeti) müşteri tarafından CSV/Excel ile yüklenir (ADR-007).
Kategori komisyon oranı platformdan gelir, müşteri override edebilir.
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint(
            "platform_connection_id",
            "external_id",
            name="uq_product_connection_external",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    platform_connection_id: Mapped[int] = mapped_column(
        ForeignKey("platform_connection.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.20"),
        server_default="0.20",
        nullable=False,
    )
    cogs: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
