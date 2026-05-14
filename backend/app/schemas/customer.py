"""
Customer için Pydantic schema'ları.

Base   → ortak alanlar
Create → yeni müşteri oluşturma input'u
Update → kısmi güncelleme (tüm alanlar opsiyonel)
Read   → API'den döndürülen tam müşteri kaydı
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    is_vat_registered: bool = True
    stopaj_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=4)
    default_shipping_cost: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_vat_registered: bool | None = None
    stopaj_rate: Decimal | None = Field(default=None, ge=0, le=1, decimal_places=4)
    default_shipping_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
