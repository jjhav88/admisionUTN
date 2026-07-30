"""Esquemas de configuración del sitio."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SiteSettingsUpdate(BaseModel):
    """Actualización de textos de header/footer y contacto."""

    header_title: str | None = Field(default=None, max_length=200)
    footer_title: str | None = Field(default=None, max_length=255)
    footer_org: str | None = Field(default=None, max_length=255)
    footer_copy: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=80)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_address: str | None = None

    @field_validator(
        "header_title",
        "footer_title",
        "footer_org",
        "footer_copy",
        "contact_phone",
        "contact_email",
        "contact_address",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class SiteSettingsRead(BaseModel):
    """Configuración serializada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    header_logo_url: str | None = None
    header_title: str | None = None
    footer_logo_url: str | None = None
    footer_title: str | None = None
    footer_org: str | None = None
    footer_copy: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    contact_address: str | None = None
    whatsapp_url: str | None = None
    updated_at: datetime | None = None
