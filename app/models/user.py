"""Modelo de usuario del sistema de admisión."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    """Roles soportados (equivalente simplificado a tabla Role)."""

    ADMIN = "admin"
    SPECIALIST = "specialist"


class User(Base):
    """Usuario autenticable con rol y estado activo."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    password_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.SPECIALIST, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    permissions = relationship("Permission", back_populates="user", cascade="all, delete-orphan")

    @property
    def role_name(self) -> str:
        """Nombre del rol para autorización (admin|specialist)."""
        return self.role.value if isinstance(self.role, UserRole) else str(self.role)
