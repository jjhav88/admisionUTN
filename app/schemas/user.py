"""Esquemas Pydantic de usuario (Create / Update / Read)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Campos comunes de usuario."""

    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    full_name: str | None = None
    role: UserRole = UserRole.SPECIALIST
    is_active: bool = True
    avatar_url: str | None = None


class UserCreate(UserBase):
    """Alta de usuario con contraseña."""

    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    """Actualización parcial de usuario (admin)."""

    username: str | None = Field(default=None, min_length=3, max_length=80)
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    avatar_url: str | None = None


class ProfileUpdate(BaseModel):
    """Actualización del propio perfil (sin cambiar rol ni estado)."""

    username: str | None = Field(default=None, min_length=3, max_length=80)
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserRead(UserBase):
    """Usuario serializado para respuestas API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None


class UserAdminRead(UserRead):
    """Usuario para panel admin, incluye contraseña recuperable."""

    password: str | None = None
