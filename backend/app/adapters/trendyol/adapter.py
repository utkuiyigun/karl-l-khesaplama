"""
Trendyol adaptörü — ham Trendyol JSON'unu iç modele dönüştürür.

Implementation rehberi: docs/TRENDYOL_API_NOTLAR.md

TODO[claude-code]:
1. Önce tests/integration/test_trendyol_adapter.py altında fixture-based testler yaz
   - tests/fixtures/trendyol_orders/*.json gerçek (anonim) Trendyol response'ları
   - Her fixture için beklenen Order çıktısı
2. TrendyolAdapter sınıfını implement et
3. fetch_orders: client.list_orders() çağır, response'u Order'a map et
4. Statü mapping'i: Trendyol → PackageStatus enum'u
"""
from datetime import datetime

from app.adapters.base.adapter import MarketplaceAdapter
from app.adapters.base.types import Order


class TrendyolAdapter(MarketplaceAdapter):
    def __init__(self, api_key: str, api_secret: str, seller_id: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.seller_id = seller_id
        # TODO: TrendyolClient instance'ı oluştur

    async def fetch_orders(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Order]:
        raise NotImplementedError("TODO[claude-code]")

    async def fetch_products(self) -> list[dict]:
        raise NotImplementedError("TODO[claude-code]")

    def get_platform_name(self) -> str:
        return "trendyol"
