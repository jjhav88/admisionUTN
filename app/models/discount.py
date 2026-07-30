"""Modelo de descuentos asociados a carreras (y opcionalmente categorías)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Discount(Base):
    """Descuento porcentual con vigencia opcional."""

    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="Descuento")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    career = relationship("Career", back_populates="discounts")
    category = relationship("Category", back_populates="discounts")

    @property
    def career_name(self) -> str | None:
        return self.career.name if self.career else None

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None
