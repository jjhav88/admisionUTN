"""Servicio de configuración visual del sitio."""

from sqlalchemy.orm import Session

from app.models.site_settings import SiteSettings
from app.repositories.site_settings_repository import SiteSettingsRepository
from app.schemas.site_settings import SiteSettingsUpdate


DEFAULT_FOOTER_TITLE = "Sistema de Gestión de Información para Admisiones"
DEFAULT_FOOTER_ORG = "Universidad Tominaga Nakamoto"
DEFAULT_FOOTER_COPY = "All Rights Reserved ®"


class SiteSettingsService:
    """Lee y actualiza la configuración singleton del sitio."""

    def __init__(self, db: Session):
        self.repo = SiteSettingsRepository(db)

    def get_or_create(self) -> SiteSettings:
        """Obtiene la configuración o crea valores por defecto."""
        settings = self.repo.get()
        if settings:
            return settings
        return self.repo.create(
            SiteSettings(
                id=1,
                header_title=None,
                footer_title=DEFAULT_FOOTER_TITLE,
                footer_org=DEFAULT_FOOTER_ORG,
                footer_copy=DEFAULT_FOOTER_COPY,
            )
        )

    def update(self, data: SiteSettingsUpdate) -> SiteSettings:
        """Actualiza textos de header/footer/contacto."""
        settings = self.get_or_create()
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            if isinstance(value, str):
                value = value.strip() or None
            setattr(settings, key, value)
        return self.repo.save(settings)

    def set_header_logo(self, url: str) -> SiteSettings:
        settings = self.get_or_create()
        settings.header_logo_url = url
        return self.repo.save(settings)

    def set_footer_logo(self, url: str) -> SiteSettings:
        settings = self.get_or_create()
        settings.footer_logo_url = url
        return self.repo.save(settings)
