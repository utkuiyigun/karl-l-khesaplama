"""
Ortak Pydantic schema parçaları.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Liste endpoint'lerinin sayfalama parametreleri."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class Page(BaseModel, Generic[T]):
    """Sayfalanmış sonuç sarmalayıcı."""

    items: list[T]
    total: int
    limit: int
    offset: int
