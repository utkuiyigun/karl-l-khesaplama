"""
Melon-Kar Backend — FastAPI app entry point.
"""
from fastapi import FastAPI

from app.api.v1 import cogs, connections, customers, reports
from app.core.config import settings

app = FastAPI(
    title="Melon-Kar API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# v1 router'ları
app.include_router(customers.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(cogs.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
