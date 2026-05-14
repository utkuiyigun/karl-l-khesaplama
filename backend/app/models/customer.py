"""
Customer — ajans müşterisi (panele giriş yapan kişi).

Auth: NextAuth magic link kullanılacak (ADR-009), bu yüzden password_hash YOK.
"""
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Vergi davranışı — hesaplama motoru bu alanları okur
    is_vat_registered: Mapped[bool] = mapped_column(default=True, nullable=False)
    stopaj_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    default_shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
