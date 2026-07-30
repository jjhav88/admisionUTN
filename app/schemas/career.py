"""Esquemas Pydantic de carreras."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.career import CareerLevel


class CareerBase(BaseModel):
    """Campos base de carrera."""

    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    level: CareerLevel = CareerLevel.LICENCIATURA
    is_active: bool = True


class CareerCreate(CareerBase):
    """Alta de carrera."""

    pass


class CareerUpdate(BaseModel):
    """Actualización parcial de carrera."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    level: CareerLevel | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CareerReorder(BaseModel):
    """Lista ordenada de IDs para reordenar carreras."""

    ids: list[int] = Field(min_length=1)


class CareerRead(CareerBase):
    """Carrera para respuestas API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    sort_order: int = 0
    image_url: str | None = None
    level_label: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
