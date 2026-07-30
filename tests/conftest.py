"""Configuración de pytest: base de datos aislada (no toca admitomi.db)."""

from __future__ import annotations

import os
from pathlib import Path

# Debe ejecutarse antes de importar la app / engine.
TEST_DB_PATH = Path(__file__).resolve().parent / "test_admitomi.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core import database as db_module  # noqa: E402
from app.core.schema_migrate import ensure_schema  # noqa: E402
from app.models import Base  # noqa: E402
from seed import run_seed  # noqa: E402

_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
db_module.engine = create_engine(_settings.database_url, connect_args=_connect_args)
db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)

import main  # noqa: E402

main.engine = db_module.engine
main.SessionLocal = db_module.SessionLocal


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    """Prepara una BD de prueba limpia al iniciar la sesión."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=db_module.engine)
    ensure_schema(db_module.engine)
    db = db_module.SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    """Elimina el archivo SQLite de pruebas al terminar."""
    db_module.engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink(missing_ok=True)
