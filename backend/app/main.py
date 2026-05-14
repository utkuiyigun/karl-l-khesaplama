"""
Melon-Kar Backend — FastAPI app entry point.

Bu dosya iskelet olarak konuldu. Claude Code geliştirme sırasında genişletecek.
"""
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title="Melon-Kar API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# TODO: Claude Code router'ları buraya bağlayacak
# from app.api.v1 import auth, customers, connections, orders, products, reports, simulations
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# ...
