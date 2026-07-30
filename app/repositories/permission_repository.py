"""Repositorio de acceso a datos para permisos de edición."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.permission import Permission


class PermissionRepository:
    """Operaciones CRUD y consultas de Permission."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, permission_id: int) -> Permission | None:
        return self.db.get(Permission, permission_id)

    def get(self, user_id: int, career_id: int, category_id: int) -> Permission | None:
        """Busca permiso exacto usuario+carrera+categoría."""
        return self.db.scalar(
            select(Permission).where(
                Permission.user_id == user_id,
                Permission.career_id == career_id,
                Permission.category_id == category_id,
            )
        )

    def list_all(self) -> list[Permission]:
        return list(
            self.db.scalars(
                select(Permission)
                .options(
                    joinedload(Permission.user),
                    joinedload(Permission.career),
                    joinedload(Permission.category),
                )
                .order_by(Permission.id.desc())
            )
            .unique()
            .all()
        )

    def list_by_user(self, user_id: int) -> list[Permission]:
        return list(
            self.db.scalars(
                select(Permission)
                .options(joinedload(Permission.career), joinedload(Permission.category))
                .where(Permission.user_id == user_id)
            )
            .unique()
            .all()
        )

    def create(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def save(self, permission: Permission) -> Permission:
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete(self, permission: Permission) -> None:
        self.db.delete(permission)
        self.db.commit()
