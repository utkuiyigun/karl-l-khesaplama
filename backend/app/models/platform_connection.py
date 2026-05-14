"""
PlatformConnection — bir müşterinin bir pazaryeri (Trendyol/Shopify) bağlantısı.

API key/secret Fernet ile şifreli saklanır (ADR-006).
sync_start_date: bağlantı kurulduğu an; geçmiş veri çekilmez (ADR-003).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PlatformConnection(Base, TimestampMixin):
    __tablename__ = "platform_connection"
    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "platform",
            "seller_id",
            name="uq_platform_connection_customer_platform_seller",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    platform: Mapped[str] = mapped_column(String(32), nullable=False)  # "trendyol" | "shopify"
    seller_id: Mapped[str] = mapped_column(String(64), nullable=False)

    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    sync_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
