"""Esquemas Pydantic para información de carrera por categoría."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CareerInfoBase(BaseModel):
    """Campos base del contenido por categoría."""

    content: str | None = None
    extra_data: dict[str, Any] | None = None
    sort_order: int = 0


class CareerInfoCreate(CareerInfoBase):
    """Payload para crear información de carrera."""

    career_id: int
    category_id: int


class CareerInfoUpdate(BaseModel):
    """Payload parcial/total para editar contenido."""

    content: str | None = None
    extra_data: dict[str, Any] | None = None
    sort_order: int | None = None


class CareerInfoRead(CareerInfoBase):
    """Representación de lectura de CareerInfo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    career_id: int
    category_id: int
    updated_at: datetime | None = None


class CareerInfoGrouped(BaseModel):
    """Info de una categoría dentro del detalle de carrera."""

    category_id: int
    category_name: str
    content: str | None = None
    extra_data: dict[str, Any] | None = None
    sort_order: int = 0
    can_edit: bool = False
    allows_document: bool = False
    field_type: str = "long_text"
    field_options: list[str] = Field(default_factory=list)
    selected_values: list[str] = Field(default_factory=list)
    info_id: int | None = None
    updated_at: datetime | None = None


class CareerDetailRead(BaseModel):
    """Carrera con su información agrupada por categoría."""

    id: int
    name: str
    slug: str
    description: str | None = None
    level: str | None = None
    categories: list[CareerInfoGrouped] = Field(default_factory=list)
