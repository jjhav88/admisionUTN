"""Modelo de categoría dinámica de información."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base


class CategoryFieldType(str, enum.Enum):
    """Tipo de dato que se captura al registrar información."""

    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    SELECT_LIST = "select_list"
    WEEKDAY_HOURS = "weekday_hours"
    FILE = "file"
    ITEM_LIST = "item_list"

    @property
    def label(self) -> str:
        return {
            CategoryFieldType.SHORT_TEXT: "Texto corto",
            CategoryFieldType.LONG_TEXT: "Texto largo",
            CategoryFieldType.SINGLE_SELECT: "Selección única",
            CategoryFieldType.MULTI_SELECT: "Selección múltiple",
            CategoryFieldType.SELECT_LIST: "Lista de selección",
            CategoryFieldType.WEEKDAY_HOURS: "Días y horario",
            CategoryFieldType.FILE: "Archivo",
            CategoryFieldType.ITEM_LIST: "Lista de elementos",
        }[self]


class Category(Base):
    """Categoría reutilizable (requisitos, costos, becas, etc.)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_document: Mapped[bool] = mapped_column(Boolean, default=False)
    field_type: Mapped[CategoryFieldType] = mapped_column(
        Enum(
            CategoryFieldType,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=40,
        ),
        default=CategoryFieldType.LONG_TEXT,
        index=True,
    )
    field_options: Mapped[list | None] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    infos = relationship("CareerInfo", back_populates="category", cascade="all, delete-orphan")
    discounts = relationship("Discount", back_populates="category")
    permissions = relationship("Permission", back_populates="category", cascade="all, delete-orphan")

    @property
    def field_type_label(self) -> str:
        if isinstance(self.field_type, CategoryFieldType):
            return self.field_type.label
        try:
            return CategoryFieldType(self.field_type).label
        except ValueError:
            return str(self.field_type)

    @property
    def options_list(self) -> list[str]:
        raw = self.field_options or []
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]
