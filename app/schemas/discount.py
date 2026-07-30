"""Esquemas Pydantic de descuentos."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DiscountBase(BaseModel):
    career_id: int
    category_id: int | None = None
    title: str = Field(default="Descuento", max_length=200)
    percentage: Decimal = Field(ge=0, le=100)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    is_active: bool = True


class DiscountCreate(DiscountBase):
    pass


class DiscountUpdate(BaseModel):
    career_id: int | None = None
    category_id: int | None = None
    title: str | None = Field(default=None, max_length=200)
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    is_active: bool | None = None


class DiscountRead(DiscountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    career_name: str | None = None
    category_name: str | None = None
