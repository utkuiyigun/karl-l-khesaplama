"""
Trendyol Marketplace API için async HTTP client.

Sorumluluğu:
- HTTP Basic Auth header'ı
- User-Agent header'ı (Trendyol zorunlu kılıyor)
- Retry / rate-limit handling
- Pagination yardımcıları
- Tarih chunk'lama (14 günlük pencereler)

DOĞRUDAN İŞ MANTIĞI BURADA OLMAZ — sadece HTTP. Mapping ayrı dosyada (adapter.py).
"""
import base64
from datetime import datetime, timedelta
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings


class TrendyolClient:
    def __init__(self, api_key: str, api_secret: str, seller_id: str):
        self.seller_id = seller_id
        token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        self._client = httpx.AsyncClient(
            base_url=settings.trendyol_base_url,
            headers={
                "Authorization": f"Basic {token}",
                "User-Agent": f"{seller_id} - {settings.trendyol_user_agent_suffix}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
    )
    async def list_orders(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 0,
        size: int = 200,
        order_by_field: str = "PackageLastModifiedDate",
        order_by_direction: str = "DESC",
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        GET /suppliers/{supplierId}/orders
        
        NOT: start/end tarih aralığı MAKS 14 GÜN. Daha geniş için chunk'la.
        """
        params: dict[str, Any] = {
            "startDate": int(start_date.timestamp() * 1000),
            "endDate": int(end_date.timestamp() * 1000),
            "page": page,
            "size": size,
            "orderByField": order_by_field,
            "orderByDirection": order_by_direction,
        }
        if status:
            params["status"] = status

        resp = await self._client.get(
            f"/suppliers/{self.seller_id}/orders",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def chunk_date_range(
    start: datetime,
    end: datetime,
    chunk_days: int = 13,
) -> list[tuple[datetime, datetime]]:
    """14 günlük limiti aşmamak için tarih aralığını parçala."""
    chunks: list[tuple[datetime, datetime]] = []
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        chunks.append((current, chunk_end))
        current = chunk_end
    return chunks
