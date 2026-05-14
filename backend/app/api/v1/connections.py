"""
PlatformConnection CRUD endpoint'leri.

Nested: /customers/{customer_id}/connections

GÜVENLİK:
- api_key / api_secret KAYDEDİLMEDEN ÖNCE Fernet ile şifrelenir (ADR-006)
- Response'ta KESİNLİKLE plain text'i döndürülmez
- Plain text'i hiçbir yerde loglanmaz
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_secret
from app.db.session import get_db
from app.models.customer import Customer
from app.models.platform_connection import PlatformConnection
from app.schemas.platform_connection import (
    PlatformConnectionCreate,
    PlatformConnectionRead,
    PlatformConnectionUpdate,
)

router = APIRouter(
    prefix="/customers/{customer_id}/connections",
    tags=["platform-connections"],
)


async def _get_customer_or_404(customer_id: int, db: AsyncSession) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    return customer


async def _get_connection_or_404(
    customer_id: int,
    connection_id: int,
    db: AsyncSession,
) -> PlatformConnection:
    """ADR-008: customer_id filtresi ZORUNLU — bir müşteri başkasının bağlantısını göremez."""
    conn = await db.get(PlatformConnection, connection_id)
    if conn is None or conn.customer_id != customer_id:
        raise HTTPException(status_code=404, detail="Bağlantı bulunamadı.")
    return conn


@router.post("", response_model=PlatformConnectionRead, status_code=status.HTTP_201_CREATED)
async def create_connection(
    customer_id: int,
    payload: PlatformConnectionCreate,
    db: AsyncSession = Depends(get_db),
) -> PlatformConnection:
    await _get_customer_or_404(customer_id, db)

    connection = PlatformConnection(
        customer_id=customer_id,
        platform=payload.platform,
        seller_id=payload.seller_id,
        api_key_encrypted=encrypt_secret(payload.api_key),
        api_secret_encrypted=encrypt_secret(payload.api_secret),
        is_active=payload.is_active,
        sync_start_date=payload.sync_start_date or datetime.now(timezone.utc),
    )
    db.add(connection)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu müşteri için aynı platform + seller_id ile bağlantı zaten var.",
        ) from exc
    await db.refresh(connection)
    return connection


@router.get("", response_model=list[PlatformConnectionRead])
async def list_connections(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[PlatformConnection]:
    await _get_customer_or_404(customer_id, db)

    query = (
        select(PlatformConnection)
        .where(PlatformConnection.customer_id == customer_id)
        .order_by(PlatformConnection.id.desc())
    )
    return list((await db.execute(query)).scalars().all())


@router.patch("/{connection_id}", response_model=PlatformConnectionRead)
async def update_connection(
    customer_id: int,
    connection_id: int,
    payload: PlatformConnectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> PlatformConnection:
    connection = await _get_connection_or_404(customer_id, connection_id, db)

    updates = payload.model_dump(exclude_unset=True)
    if "api_key" in updates:
        connection.api_key_encrypted = encrypt_secret(updates.pop("api_key"))
    if "api_secret" in updates:
        connection.api_secret_encrypted = encrypt_secret(updates.pop("api_secret"))
    for key, value in updates.items():
        setattr(connection, key, value)

    await db.commit()
    await db.refresh(connection)
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    customer_id: int,
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    connection = await _get_connection_or_404(customer_id, connection_id, db)
    await db.delete(connection)
    await db.commit()
