"""
PlatformConnection için Pydantic schema'ları.

GÜVENLİK: api_key ve api_secret SADECE Create'te (input) ve Update'te kabul edilir.
Read response'unda KESİNLİKLE döndürülmez (ADR-006).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Faz 1: sadece trendyol. Shopify Faz 2'de eklenecek.
PlatformName = Literal["trendyol"]


class PlatformConnectionBase(BaseModel):
    platform: PlatformName
    seller_id: str = Field(min_length=1, max_length=64)


class PlatformConnectionCreate(PlatformConnectionBase):
    """API key/secret plain text gelir, biz Fernet ile şifreleyip saklarız."""

    api_key: str = Field(min_length=1, max_length=512)
    api_secret: str = Field(min_length=1, max_length=512)
    sync_start_date: datetime | None = None  # None ise endpoint now() koyar
    is_active: bool = True


class PlatformConnectionUpdate(BaseModel):
    """Bağlantı güncellemesi — key rotation veya aktif/pasif toggle için."""

    api_key: str | None = Field(default=None, min_length=1, max_length=512)
    api_secret: str | None = Field(default=None, min_length=1, max_length=512)
    is_active: bool | None = None


class PlatformConnectionRead(PlatformConnectionBase):
    """API key/secret KESİNLİKLE yok. Müşteri panelinde 'bağlandı' diye gözükür yeter."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    is_active: bool
    sync_start_date: datetime
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime
