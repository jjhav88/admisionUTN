"""Configuración de la aplicación cargada desde variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

INSECURE_SECRET_KEYS = {
    "dev-secret-change-me",
    "change-me-to-a-long-random-string",
    "dev-secret-admitomi-change-in-production",
    "change-me-in-production",
}


class Settings(BaseSettings):
    """Settings globales (DB, JWT, CORS, uploads)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AdmiTomi"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = f"sqlite:///{BASE_DIR / 'admitomi.db'}"
    upload_dir: str = str(BASE_DIR / "app" / "static" / "uploads")
    debug: bool = True
    cookie_name: str = "access_token"
    # Orígenes permitidos para CORS (separados por coma en .env)
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    # Rate limit de login (formato slowapi)
    login_rate_limit: str = "10/minute"
    # Seed: password del admin inicial (solo si el usuario no existe)
    admin_password: str = "admin123"
    admin_email: str = "admin@admitomi.com"
    # Limpieza de residuos de tests en seed (por defecto: solo en DEBUG)
    seed_cleanup_tests: bool | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """Lista de orígenes CORS a partir de la cadena configurada."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def should_cleanup_tests(self) -> bool:
        if self.seed_cleanup_tests is not None:
            return self.seed_cleanup_tests
        return self.debug

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """En producción exige SECRET_KEY fuerte."""
        if not self.debug and self.secret_key.strip() in INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY inseguro para producción. Define un valor aleatorio largo "
                "y DEBUG=false en las variables de entorno."
            )
        if not self.debug and len(self.secret_key.strip()) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres en producción.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna Settings cacheado."""
    return Settings()
