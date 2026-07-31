"""Servicio de permisos granulares por usuario/carrera/categoría."""

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.permission import Permission
from app.models.user import User, UserRole
from app.repositories.permission_repository import PermissionRepository
from app.schemas.permission import PermissionBulkCreate, PermissionCreate, PermissionUpdate


class PermissionService:
    """Verifica y administra permisos de edición (can_edit)."""

    def __init__(self, db: Session):
        self.repo = PermissionRepository(db)

    def can_edit(self, user: User, career_id: int, category_id: int) -> bool:
        """Admin siempre puede; specialist solo con Permission.can_edit=True."""
        if user.role_name == UserRole.ADMIN.value:
            return True
        permission = self.repo.get(user.id, career_id, category_id)
        return bool(permission and permission.can_edit)

    def require_edit(self, user: User, career_id: int, category_id: int) -> None:
        """Lanza ForbiddenError si el usuario no puede editar esa combinación."""
        if not self.can_edit(user, career_id, category_id):
            raise ForbiddenError("Sin permiso de edición para esta categoría")

    def list_all(self) -> list[Permission]:
        """Lista todos los permisos asignados."""
        return self.repo.list_all()

    def list_for_user(self, user_id: int) -> list[Permission]:
        """Lista permisos de un usuario."""
        return self.repo.list_by_user(user_id)

    def create(self, data: PermissionCreate) -> Permission:
        """Asigna o actualiza un permiso (upsert por unique constraint)."""
        existing = self.repo.get(data.user_id, data.career_id, data.category_id)
        if existing:
            existing.can_edit = data.can_edit
            return self.repo.save(existing)
        return self.repo.create(Permission(**data.model_dump()))

    def create_bulk(self, data: PermissionBulkCreate) -> list[Permission]:
        """Sincroniza permisos: deja solo las categorías marcadas en las carreras elegidas."""

        def unique(ids: list[int]) -> list[int]:
            seen: set[int] = set()
            ordered: list[int] = []
            for item_id in ids:
                if item_id in seen:
                    continue
                seen.add(item_id)
                ordered.append(item_id)
            return ordered

        category_ids = unique(data.category_ids)
        career_ids = unique(data.career_ids)
        allowed = set(category_ids)

        # Revocar lo que ya no está marcado (en las carreras del formulario).
        for permission in self.repo.list_by_user_and_careers(data.user_id, career_ids):
            if permission.category_id not in allowed:
                self.repo.delete(permission)

        created: list[Permission] = []
        for category_id in category_ids:
            for career_id in career_ids:
                created.append(
                    self.create(
                        PermissionCreate(
                            user_id=data.user_id,
                            career_id=career_id,
                            category_id=category_id,
                            can_edit=data.can_edit,
                        )
                    )
                )
        return created

    def update(self, permission_id: int, data: PermissionUpdate) -> Permission:
        """Actualiza un permiso existente."""
        permission = self.repo.get_by_id(permission_id)
        if not permission:
            raise NotFoundError("Permiso no encontrado")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(permission, key, value)
        return self.repo.save(permission)

    def delete(self, permission_id: int) -> None:
        """Revoca un permiso."""
        permission = self.repo.get_by_id(permission_id)
        if not permission:
            raise NotFoundError("Permiso no encontrado")
        self.repo.delete(permission)
