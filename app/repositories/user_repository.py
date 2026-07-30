"""Repositorio de acceso a datos para usuarios."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    """Operaciones CRUD y consultas de User."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list_all(
        self,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """Lista usuarios con filtros opcionales de búsqueda/rol/estado."""
        stmt = select(User).order_by(User.username)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    User.username.ilike(term),
                    User.email.ilike(term),
                    User.full_name.ilike(term),
                )
            )
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        return list(self.db.scalars(stmt).all())

    def count_admins(self) -> int:
        """Cuenta administradores activos (para no dejar el sistema sin admin)."""
        return len(
            list(
                self.db.scalars(
                    select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
                ).all()
            )
        )

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
