"""Repositorio de configuración del sitio."""

from sqlalchemy.orm import Session

from app.models.site_settings import SiteSettings


class SiteSettingsRepository:
    """Acceso a la fila única de SiteSettings."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> SiteSettings | None:
        return self.db.get(SiteSettings, 1)

    def create(self, settings: SiteSettings) -> SiteSettings:
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def save(self, settings: SiteSettings) -> SiteSettings:
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings
