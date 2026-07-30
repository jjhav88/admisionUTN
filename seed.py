"""Seed inicial: usuario administrador y limpieza opcional de residuos de tests."""

import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_password_for_admin, get_password_hash
from app.models.career import Career
from app.models.career_info import CareerInfo
from app.models.category import Category
from app.models.discount import Discount
from app.models.permission import Permission
from app.models.user import User, UserRole
from app.services.site_settings_service import SiteSettingsService

# Usuarios creados por pytest cuando aún compartían la BD de desarrollo.
TEST_USER_PREFIXES = (
    "u_deny_",
    "u_disc_",
    "u_perm_",
    "u_crud_",
    "u_prof_",
    "u_esp_",
    "u_bulk_",
    "u_b2_",
)

# Carreras generadas por tests (nombre + sufijo hex).
TEST_CAREER_PREFIXES = (
    "Carrera Perm ",
    "Carrera A ",
    "Carrera B ",
    "C1 ",
    "C2 ",
    "Car1 ",
    "Car2 ",
)

# Categorías generadas por tests.
TEST_CATEGORY_PREFIXES = (
    "Cat A ",
    "Cat B ",
    "CatBulk ",
    "Cat1 ",
    "Cat2 ",
)

TEST_CATEGORY_BASES_WITH_SUFFIX = (
    "Cat",
)


def _has_test_suffix(name: str, base: str) -> bool:
    return bool(re.fullmatch(rf"{re.escape(base)}[0-9a-f]{{6,}}", name, flags=re.I))


def _delete_career(db: Session, career: Career) -> None:
    db.execute(delete(Permission).where(Permission.career_id == career.id))
    db.execute(delete(Discount).where(Discount.career_id == career.id))
    db.execute(delete(CareerInfo).where(CareerInfo.career_id == career.id))
    db.delete(career)


def _delete_category(db: Session, category: Category) -> None:
    db.execute(delete(Permission).where(Permission.category_id == category.id))
    db.execute(delete(Discount).where(Discount.category_id == category.id))
    db.execute(delete(CareerInfo).where(CareerInfo.category_id == category.id))
    db.delete(category)


def run_seed(db: Session) -> None:
    """Crea admin inicial si falta y opcionalmente limpia basura de tests."""
    settings = get_settings()
    admin_password = settings.admin_password or "admin123"

    admin = db.scalar(select(User).where(User.username == "admin"))
    if not admin:
        db.add(
            User(
                username="admin",
                email=settings.admin_email,
                full_name="Administrador",
                role=UserRole.ADMIN,
                hashed_password=get_password_hash(admin_password),
                password_encrypted=encrypt_password_for_admin(admin_password),
                is_active=True,
            )
        )
    elif not admin.password_encrypted:
        # Solo rellena recuperación si aún no existe (no resetea password).
        admin.password_encrypted = encrypt_password_for_admin(admin_password)

    SiteSettingsService(db).get_or_create()

    if settings.should_cleanup_tests:
        for user in list(db.scalars(select(User).where(User.username != "admin")).all()):
            if not any(user.username.startswith(prefix) for prefix in TEST_USER_PREFIXES):
                continue
            db.execute(delete(Permission).where(Permission.user_id == user.id))
            db.delete(user)

        for career in list(db.scalars(select(Career)).all()):
            if any(career.name.startswith(prefix) for prefix in TEST_CAREER_PREFIXES):
                _delete_career(db, career)

        for category in list(db.scalars(select(Category)).all()):
            if any(category.name.startswith(prefix) for prefix in TEST_CATEGORY_PREFIXES):
                _delete_category(db, category)
                continue
            if any(_has_test_suffix(category.name, base) for base in TEST_CATEGORY_BASES_WITH_SUFFIX):
                _delete_category(db, category)

        demo = db.scalar(select(Career).where(Career.slug == "ingenieria-en-sistemas"))
        if demo:
            _delete_career(db, demo)

    db.commit()
