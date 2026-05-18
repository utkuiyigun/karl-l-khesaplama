"""
Melon-Kar Backend — FastAPI app entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import cogs, connections, customers, price_simulator, reports
from app.core.config import settings

app = FastAPI(
    title="Melon-Kar API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)

# Frontend dev sunucusu için CORS (Next.js varsayılan port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# v1 router'ları
app.include_router(customers.router, prefix="/api/v1")
app.include_router(connections.router, prefix="/api/v1")
app.include_router(cogs.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(price_simulator.router, prefix="/api/v1")
