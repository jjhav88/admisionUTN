"""Modelo de permiso fino de edición por usuario/carrera/categoría."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Permission(Base):
    """Autoriza a un especialista editar una categoría de una carrera."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "career_id", "category_id", name="uq_user_career_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    career_id: Mapped[int] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="permissions")
    career = relationship("Career", back_populates="permissions")
    category = relationship("Category", back_populates="permissions")
