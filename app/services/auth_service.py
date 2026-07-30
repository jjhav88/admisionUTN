"""Servicio de autenticación y gestión de usuarios (sin dependencias FastAPI)."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    decrypt_password_for_admin,
    encrypt_password_for_admin,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import ProfileUpdate, UserAdminRead, UserCreate, UserUpdate


class AuthService:
    """Lógica de negocio para login, tokens y CRUD de usuarios."""

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> User:
        """Valida credenciales y retorna el usuario activo."""
        user = self.repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Usuario o contraseña incorrectos")
        if not user.is_active:
            raise ForbiddenError("Usuario inactivo")
        return user

    def create_token_for_user(self, user: User) -> str:
        """Emite un JWT Bearer para el usuario."""
        return create_access_token(user.id)

    @staticmethod
    def to_admin_read(user: User) -> UserAdminRead:
        """Serializa usuario incluyendo contraseña recuperable para admin."""
        data = UserAdminRead.model_validate(user)
        data.password = decrypt_password_for_admin(user.password_encrypted)
        return data

    def create_user(self, data: UserCreate) -> User:
        """Crea un usuario nuevo validando unicidad de username/email."""
        if self.repo.get_by_username(data.username):
            raise ConflictError("El nombre de usuario ya existe")
        if self.repo.get_by_email(data.email):
            raise ConflictError("El email ya está registrado")
        user = User(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active,
            avatar_url=data.avatar_url,
            hashed_password=get_password_hash(data.password),
            password_encrypted=encrypt_password_for_admin(data.password),
        )
        return self.repo.create(user)

    def update_user(self, user_id: int, data: UserUpdate, actor: User | None = None) -> User:
        """Actualiza un usuario; protege el último admin y valida unicidad."""
        user = self.get_user(user_id)
        payload = data.model_dump(exclude_unset=True)
        password = payload.pop("password", None)

        if "username" in payload and payload["username"] != user.username:
            if self.repo.get_by_username(payload["username"]):
                raise ConflictError("El nombre de usuario ya existe")

        if "email" in payload and payload["email"] != user.email:
            if self.repo.get_by_email(payload["email"]):
                raise ConflictError("El email ya está registrado")

        # No degradar/desactivar el último administrador activo
        becoming_non_admin = (
            "role" in payload
            and payload["role"] != UserRole.ADMIN
            and user.role == UserRole.ADMIN
        )
        becoming_inactive = "is_active" in payload and payload["is_active"] is False and user.is_active
        if user.role == UserRole.ADMIN and user.is_active and (becoming_non_admin or becoming_inactive):
            if self.repo.count_admins() <= 1:
                raise ForbiddenError("No se puede dejar el sistema sin un administrador activo")

        for key, value in payload.items():
            setattr(user, key, value)
        if password:
            user.hashed_password = get_password_hash(password)
            user.password_encrypted = encrypt_password_for_admin(password)
        return self.repo.save(user)

    def update_profile(self, user: User, data: ProfileUpdate) -> User:
        """Permite al usuario autenticado editar su propio perfil."""
        payload = data.model_dump(exclude_unset=True)
        password = payload.pop("password", None)

        if "username" in payload and payload["username"] != user.username:
            if self.repo.get_by_username(payload["username"]):
                raise ConflictError("El nombre de usuario ya existe")

        if "email" in payload and payload["email"] != user.email:
            if self.repo.get_by_email(payload["email"]):
                raise ConflictError("El email ya está registrado")

        for key, value in payload.items():
            setattr(user, key, value)
        if password:
            user.hashed_password = get_password_hash(password)
            user.password_encrypted = encrypt_password_for_admin(password)
        return self.repo.save(user)

    def list_users(
        self,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """Lista usuarios con filtros opcionales."""
        return self.repo.list_all(search=search, role=role, is_active=is_active)

    def get_user(self, user_id: int) -> User:
        """Obtiene un usuario por id o lanza NotFoundError."""
        user = self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        return user

    def set_avatar(self, user_id: int, avatar_url: str) -> User:
        """Asigna la URL de foto de perfil al usuario."""
        user = self.get_user(user_id)
        user.avatar_url = avatar_url
        return self.repo.save(user)

    def delete_user(self, user_id: int, actor: User | None = None) -> None:
        """Elimina un usuario (no a sí mismo ni al último admin)."""
        user = self.get_user(user_id)
        if actor and actor.id == user.id:
            raise ForbiddenError("No puedes eliminar tu propio usuario")
        if user.role == UserRole.ADMIN and user.is_active and self.repo.count_admins() <= 1:
            raise ForbiddenError("No se puede eliminar el único administrador activo")
        self.repo.delete(user)
