"""
Customer CRUD endpoint'leri.

NOT: Faz 1.2'de auth yok — tüm endpoint'ler açık. NextAuth magic link
sonraki fazda eklendiğinde `Depends(get_current_user)` ile koruyacağız.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.customer import Customer
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    customer = Customer(**payload.model_dump())
    db.add(customer)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-mail ile kayıtlı müşteri zaten var.",
        ) from exc
    await db.refresh(customer)
    return customer


@router.get("", response_model=Page[CustomerRead])
async def list_customers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Page[CustomerRead]:
    total_query = select(func.count()).select_from(Customer)
    total = (await db.execute(total_query)).scalar_one()

    items_query = select(Customer).order_by(Customer.id.desc()).limit(limit).offset(offset)
    items = (await db.execute(items_query)).scalars().all()

    return Page[CustomerRead](
        items=[CustomerRead.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(customer, key, value)

    await db.commit()
    await db.refresh(customer)
    return customer
