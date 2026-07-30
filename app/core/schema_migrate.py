"""Utilidad para alinear columnas nuevas en SQLite/PostgreSQL sin Alembic obligatorio."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    """Agrega columnas faltantes usadas por versiones nuevas del modelo."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    statements: list[str] = []

    if "users" in tables:
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        if "avatar_url" not in user_cols:
            statements.append("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)")
        if "password_encrypted" not in user_cols:
            statements.append("ALTER TABLE users ADD COLUMN password_encrypted VARCHAR(500)")

    if "careers" in tables:
        career_cols = {col["name"] for col in inspector.get_columns("careers")}
        if "sort_order" not in career_cols:
            statements.append("ALTER TABLE careers ADD COLUMN sort_order INTEGER DEFAULT 0")
        if "level" not in career_cols:
            statements.append(
                "ALTER TABLE careers ADD COLUMN level VARCHAR(50) DEFAULT 'licenciatura'"
            )
        if "image_url" not in career_cols:
            statements.append("ALTER TABLE careers ADD COLUMN image_url VARCHAR(500)")

    if "categories" in tables:
        category_cols = {col["name"] for col in inspector.get_columns("categories")}
        if "allows_document" not in category_cols:
            statements.append(
                "ALTER TABLE categories ADD COLUMN allows_document BOOLEAN DEFAULT 0"
            )
        if "field_type" not in category_cols:
            statements.append(
                "ALTER TABLE categories ADD COLUMN field_type VARCHAR(40) DEFAULT 'long_text'"
            )
        if "field_options" not in category_cols:
            statements.append("ALTER TABLE categories ADD COLUMN field_options JSON")

    if "discounts" in tables:
        discount_cols = {col["name"] for col in inspector.get_columns("discounts")}
        if "start_date" not in discount_cols:
            statements.append("ALTER TABLE discounts ADD COLUMN start_date DATE")
        if "end_date" not in discount_cols:
            statements.append("ALTER TABLE discounts ADD COLUMN end_date DATE")

    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
