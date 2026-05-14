"""
ShipmentPackage — bir sipariş içindeki paket.

Bir sipariş birden fazla pakete bölünebilir, her paketin statüsü farklı olabilir.
Net kâr hesabı paket bazındadır (HESAPLAMA_MOTORU §2.2).

status alanı PLATFORM-AGNOSTİK enum'u kullanır (PackageStatus).
raw_status ham platform değerini debug için saklar.
"""
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.base.types import PackageStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.order_item import OrderItem


class ShipmentPackage(Base, TimestampMixin):
    __tablename__ = "shipment_package"

    id: Mapped[int] = mapped_column(primary_key=True)

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

    external_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    status: Mapped[PackageStatus] = mapped_column(
        Enum(PackageStatus, name="package_status", native_enum=True),
        nullable=False,
    )
    raw_status: Mapped[str] = mapped_column(String(64), nullable=False)

    package_service_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )

    order: Mapped["Order"] = relationship(back_populates="packages")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
