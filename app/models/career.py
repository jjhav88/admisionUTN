"""Modelo de carrera académica."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CareerLevel(str, enum.Enum):
    """Nivel académico del programa."""

    LICENCIATURA = "licenciatura"
    MAESTRIA = "maestria"
    CURSO_POSGRADO = "curso_posgrado"
    PREPARATORIA = "preparatoria"

    @property
    def label(self) -> str:
        """Etiqueta legible para UI."""
        return {
            CareerLevel.LICENCIATURA: "Licenciatura",
            CareerLevel.MAESTRIA: "Maestría",
            CareerLevel.CURSO_POSGRADO: "Curso Posgrado",
            CareerLevel.PREPARATORIA: "Preparatoria",
        }[self]


class Career(Base):
    """Carrera/programa con slug único e información asociada."""

    __tablename__ = "careers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[CareerLevel] = mapped_column(
        Enum(
            CareerLevel,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=50,
        ),
        default=CareerLevel.LICENCIATURA,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    infos = relationship("CareerInfo", back_populates="career", cascade="all, delete-orphan")
    discounts = relationship("Discount", back_populates="career", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="career", cascade="all, delete-orphan")

    @property
    def level_label(self) -> str:
        """Nombre visible del nivel."""
        if isinstance(self.level, CareerLevel):
            return self.level.label
        try:
            return CareerLevel(self.level).label
        except ValueError:
            return str(self.level)
