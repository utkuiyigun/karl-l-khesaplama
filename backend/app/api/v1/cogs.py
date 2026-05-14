"""
COGS yükleme endpoint'leri.

Endpoint'ler:
- GET  /customers/{customer_id}/cogs/template  → boş CSV şablonu indirir
- POST /customers/{customer_id}/cogs           → CSV veya Excel yükle, ürünleri günceller
"""
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.customer import Customer
from app.services.cogs_import import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_BYTES,
    CogsImportError,
    import_cogs_for_customer,
    parse_cogs_file,
)

router = APIRouter(prefix="/customers/{customer_id}/cogs", tags=["cogs"])

CSV_TEMPLATE = "barcode,name,cogs\nABC123,Ornek urun,42.50\nXYZ789,Diger urun,15.00\n"


@router.get("/template")
async def download_template() -> StreamingResponse:
    """COGS yüklemesi için boş CSV şablonu döner."""
    return StreamingResponse(
        BytesIO(CSV_TEMPLATE.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cogs_template.csv"},
    )


@router.post("", status_code=status.HTTP_200_OK)
async def upload_cogs(
    customer_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenen formatlar: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya {MAX_FILE_BYTES // (1024 * 1024)} MB'den büyük olamaz.",
        )

    try:
        df = parse_cogs_file(content, file.filename)
        result = await import_cogs_for_customer(db, customer_id, df)
    except CogsImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result
