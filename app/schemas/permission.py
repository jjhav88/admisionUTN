"""Esquemas Pydantic de permisos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionBase(BaseModel):
    user_id: int
    career_id: int
    category_id: int
    can_edit: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionBulkCreate(BaseModel):
    """Sincroniza permisos para el producto de categorías × carreras.

    Para cada carrera seleccionada, el estado final queda exactamente como
    las categorías marcadas (las desmarcadas se revocan).
    """

    user_id: int
    category_ids: list[int] = Field(default_factory=list)
    career_ids: list[int] = Field(min_length=1)
    can_edit: bool = True


class PermissionUpdate(BaseModel):
    can_edit: bool | None = None


class PermissionRead(PermissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
