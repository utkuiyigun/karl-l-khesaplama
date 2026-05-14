"""
Order — sipariş üst seviye.

raw_data: ham platform response. Hesaplama hatası bulunursa veya formül
güncellenirse, paket/kalem verisi raw_data'dan yeniden türetilebilir.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"  # 'order' postgres'te reserved keyword
    __table_args__ = (
        UniqueConstraint(
            "platform_connection_id",
            "external_id",
            name="uq_order_connection_external",
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
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
