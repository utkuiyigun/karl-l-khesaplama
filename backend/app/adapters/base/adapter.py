"""
Tüm pazaryeri adaptörleri bu interface'i uygular.

Yeni bir platform eklemek için (Hepsiburada, Amazon, vs.):
1. adapters/{platform}/ klasörü aç
2. MarketplaceAdapter'ı subclass et
3. Ham JSON → Order dönüşümünü implement et
4. Hesaplama motoru OTOMATİK çalışır, ona dokunma.
"""
from abc import ABC, abstractmethod
from datetime import datetime

from app.adapters.base.types import Order


class MarketplaceAdapter(ABC):
    """Pazaryeri adaptörünün uyguladığı sözleşme."""

    @abstractmethod
    async def fetch_orders(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Order]:
        """Belirtilen tarih aralığındaki siparişleri çek ve iç modele dönüştür."""
        ...

    @abstractmethod
    async def fetch_products(self) -> list[dict]:
        """Ürün listesini çek (COGS eşleştirmesi için)."""
        ...

    @abstractmethod
    def get_platform_name(self) -> str:
        """Platform adı (logging için), örn 'trendyol'."""
        ...
