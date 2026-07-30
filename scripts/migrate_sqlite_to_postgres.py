"""Copia datos de SQLite local a PostgreSQL (p. ej. Render).

Uso:
  set SOURCE_DATABASE_URL=sqlite:///./admitomi.db
  set TARGET_DATABASE_URL=postgresql://...
  python scripts/migrate_sqlite_to_postgres.py

Conserva hashes de contraseña y permisos para que los logins sigan funcionando.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import Base  # noqa: E402
from app.models.career import Career  # noqa: E402
from app.models.career_info import CareerInfo  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.discount import Discount  # noqa: E402
from app.models.permission import Permission  # noqa: E402
from app.models.site_settings import SiteSettings  # noqa: E402
from app.models.user import User  # noqa: E402

# Orden por dependencias de FK
TABLE_MODELS = (
    User,
    Career,
    Category,
    SiteSettings,
    CareerInfo,
    Permission,
    Discount,
)


def _engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def _row_to_dict(obj) -> dict:
    data = {}
    for column in obj.__table__.columns:
        data[column.name] = getattr(obj, column.name)
    return data


def _normalize_pg_url(url: str) -> str:
    """Render a veces entrega postgres://; SQLAlchemy prefiere postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def migrate(source_url: str, target_url: str, *, wipe_target: bool = False) -> None:
    source_engine = _engine(source_url)
    target_engine = _engine(_normalize_pg_url(target_url))
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    Base.metadata.create_all(bind=target_engine)

    source = SourceSession()
    target = TargetSession()
    try:
        if wipe_target:
            for model in reversed(TABLE_MODELS):
                target.execute(text(f"DELETE FROM {model.__tablename__}"))
            target.commit()

        for model in TABLE_MODELS:
            rows = source.scalars(select(model)).all()
            if not rows:
                print(f"[skip] {model.__tablename__}: 0 filas")
                continue

            existing = target.scalar(select(func.count()).select_from(model)) or 0
            if existing and not wipe_target:
                raise RuntimeError(
                    f"La tabla destino '{model.__tablename__}' ya tiene {existing} filas. "
                    "Vuelve a ejecutar con WIPE_TARGET=1 solo si quieres reemplazar todo."
                )

            for row in rows:
                payload = _row_to_dict(row)
                target.merge(model(**payload))
            target.commit()
            print(f"[ok] {model.__tablename__}: {len(rows)} filas")

        print("Migración completada.")
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()


def main() -> None:
    source = os.getenv("SOURCE_DATABASE_URL", f"sqlite:///{ROOT / 'admitomi.db'}")
    target = os.getenv("TARGET_DATABASE_URL") or os.getenv("DATABASE_URL")
    wipe = os.getenv("WIPE_TARGET", "").strip() in {"1", "true", "yes", "TRUE"}

    if not target:
        raise SystemExit(
            "Define TARGET_DATABASE_URL (o DATABASE_URL) con la cadena de PostgreSQL de Render."
        )
    if target.startswith("sqlite"):
        raise SystemExit("TARGET_DATABASE_URL debe ser PostgreSQL, no SQLite.")

    print(f"Origen : {source}")
    print(f"Destino: {target.split('@')[-1] if '@' in target else target}")
    print(f"Wipe   : {wipe}")
    migrate(source, target, wipe_target=wipe)


if __name__ == "__main__":
    main()
