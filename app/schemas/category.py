"""Esquemas Pydantic de categorías."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.category import CategoryFieldType


class CategoryBase(BaseModel):
    """Campos base de categoría."""

    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    is_editable: bool = True
    allows_document: bool = False
    field_type: CategoryFieldType = CategoryFieldType.LONG_TEXT
    field_options: list[str] | None = None

    @field_validator("field_options")
    @classmethod
    def clean_options(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item and str(item).strip()]
        # Deduplica preservando orden
        seen: set[str] = set()
        unique: list[str] = []
        for item in cleaned:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    @model_validator(mode="after")
    def validate_select_options(self):
        needs_options = self.field_type in {
            CategoryFieldType.SINGLE_SELECT,
            CategoryFieldType.MULTI_SELECT,
            CategoryFieldType.SELECT_LIST,
        }
        options = self.field_options or []
        if needs_options and len(options) < 2:
            raise ValueError("Las categorías de selección requieren al menos 2 opciones")
        if not needs_options:
            self.field_options = None
        return self


class CategoryCreate(CategoryBase):
    """Alta de categoría."""

    pass


class CategoryUpdate(BaseModel):
    """Actualización parcial de categoría."""

    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    is_editable: bool | None = None
    allows_document: bool | None = None
    field_type: CategoryFieldType | None = None
    field_options: list[str] | None = None
    sort_order: int | None = None

    @field_validator("field_options")
    @classmethod
    def clean_options(cls, value: list[str] | None) -> list[str] | None:
        return CategoryBase.clean_options(value)


class CategoryReorder(BaseModel):
    """Lista ordenada de IDs para reordenar categorías."""

    ids: list[int] = Field(min_length=1)


class CategoryRead(CategoryBase):
    """Categoría para respuestas API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sort_order: int = 0
    created_at: datetime | None = None
