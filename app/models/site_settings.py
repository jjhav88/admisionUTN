"""Configuración visual del sitio (header y footer)."""

import re
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SiteSettings(Base):
    """Fila única con textos e imágenes del header/footer."""

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    header_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    header_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    footer_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    footer_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    footer_org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    footer_copy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def whatsapp_url(self) -> str | None:
        """URL de WhatsApp a partir del teléfono (solo dígitos)."""
        if not self.contact_phone:
            return None
        digits = re.sub(r"\D+", "", self.contact_phone)
        if len(digits) < 8:
            return None
        return f"https://wa.me/{digits}"
