"""
COGS (Cost of Goods Sold) toplu yükleme servisi.

ADR-007: Müşteri kendi ürün maliyetlerini CSV/Excel olarak yükler. Tek tek
elle giriş düşünülmez (yüzlerce ürün olabilir).

Beklenen kolonlar (header satırı zorunlu, büyük/küçük harf duyarsız):
- barcode    (zorunlu, string)
- cogs       (zorunlu, sayı, ≥ 0)
- name       (opsiyonel; yeni ürün yaratılırken kullanılır)

Akış:
1. Dosyayı parse et (csv/xlsx)
2. Müşterinin aktif Trendyol bağlantısını bul (yeni ürün placeholder'ı için lazım)
3. Her satır için: (customer_id, barcode) Product varsa COGS güncelle,
   yoksa placeholder Product oluştur. Sync sırasında bu placeholder otomatik
   güncellenir (sipariş geldikçe).
"""
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_connection import PlatformConnection
from app.models.product import Product

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")
REQUIRED_COLUMNS = {"barcode", "cogs"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class CogsImportError(Exception):
    """Parse veya validation hatası — kullanıcıya 400 ile döner."""


def parse_cogs_file(content: bytes, filename: str) -> pd.DataFrame:
    """CSV/Excel byte'larını pandas DataFrame'e dönüştür + kolon validasyonu."""
    name = filename.lower()
    buf = BytesIO(content)

    if name.endswith(".csv"):
        df = pd.read_csv(buf, dtype={"barcode": str})
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf, dtype={"barcode": str})
    else:
        raise CogsImportError(
            f"Desteklenmeyen format. Kabul edilenler: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise CogsImportError(
            f"Eksik kolon(lar): {', '.join(sorted(missing))}. "
            f"Zorunlu kolonlar: {', '.join(sorted(REQUIRED_COLUMNS))}"
        )

    return df


async def import_cogs_for_customer(
    session: AsyncSession,
    customer_id: int,
    df: pd.DataFrame,
) -> dict[str, Any]:
    """DataFrame'i DB'ye uygula. Hata varsa rollback, success'te commit.

    Dönen rapor: {"updated": int, "created": int, "errors": list[str]}
    """
    conn = (
        await session.execute(
            select(PlatformConnection)
            .where(
                PlatformConnection.customer_id == customer_id,
                PlatformConnection.platform == "trendyol",
                PlatformConnection.is_active.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if conn is None:
        raise CogsImportError(
            "Aktif Trendyol bağlantısı yok. Önce bir Trendyol bağlantısı kur."
        )

    updated = 0
    created = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        line_no = int(idx) + 2  # CSV satır numarası (1-indexed + header)

        barcode_raw = row.get("barcode")
        if pd.isna(barcode_raw):
            errors.append(f"Satır {line_no}: barcode boş")
            continue
        barcode = str(barcode_raw).strip()
        if not barcode:
            errors.append(f"Satır {line_no}: barcode boş")
            continue

        cogs_raw = row.get("cogs")
        if pd.isna(cogs_raw):
            errors.append(f"Satır {line_no}: cogs boş")
            continue
        try:
            cogs = Decimal(str(cogs_raw))
        except (InvalidOperation, ValueError):
            errors.append(f"Satır {line_no}: cogs sayı değil ({cogs_raw!r})")
            continue
        if cogs < 0:
            errors.append(f"Satır {line_no}: cogs negatif olamaz ({cogs})")
            continue

        existing = (
            await session.execute(
                select(Product).where(
                    Product.customer_id == customer_id,
                    Product.barcode == barcode,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.cogs = cogs
            if "name" in df.columns and pd.notna(row.get("name")):
                existing.name = str(row["name"]).strip()
            updated += 1
        else:
            name = "Unknown product"
            if "name" in df.columns and pd.notna(row.get("name")):
                name = str(row["name"]).strip() or name
            new_product = Product(
                customer_id=customer_id,
                platform_connection_id=conn.id,
                external_id=barcode,  # placeholder; Trendyol sync sırasında değişebilir
                barcode=barcode,
                name=name,
                cogs=cogs,
            )
            session.add(new_product)
            created += 1

    if errors:
        # All-or-nothing: tek satır bile hatalıysa hiçbir şey kaydetme.
        # Kullanıcı önce hataları düzeltsin, sonra tekrar yüklesin.
        await session.rollback()
        return {"updated": 0, "created": 0, "errors": errors}

    await session.commit()
    return {"updated": updated, "created": created, "errors": []}
