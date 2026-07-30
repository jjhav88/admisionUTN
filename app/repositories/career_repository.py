"""Repositorio de acceso a datos para carreras."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.career import Career, CareerLevel
from app.models.career_info import CareerInfo


class CareerRepository:
    """Operaciones CRUD y consultas de Career."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, career_id: int) -> Career | None:
        """Obtiene una carrera por id."""
        return self.db.get(Career, career_id)

    def get_by_slug(self, slug: str) -> Career | None:
        """Obtiene una carrera por slug único."""
        return self.db.scalar(select(Career).where(Career.slug == slug))

    def list_all(
        self,
        active_only: bool = False,
        search: str | None = None,
        is_active: bool | None = None,
        level: CareerLevel | None = None,
    ) -> list[Career]:
        """Lista carreras ordenadas por sort_order, con filtros opcionales."""
        stmt = select(Career).order_by(Career.sort_order, Career.name)
        if active_only or is_active is True:
            stmt = stmt.where(Career.is_active.is_(True))
        elif is_active is False:
            stmt = stmt.where(Career.is_active.is_(False))
        if level is not None:
            stmt = stmt.where(Career.level == level)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Career.name.ilike(term),
                    Career.slug.ilike(term),
                    Career.description.ilike(term),
                )
            )
        return list(self.db.scalars(stmt).all())

    def next_sort_order(self) -> int:
        """Calcula el siguiente sort_order al crear una carrera."""
        current = self.db.scalar(select(func.max(Career.sort_order)))
        return int(current or 0) + 1

    def get_with_infos(self, career_id: int) -> Career | None:
        """Obtiene carrera con infos y categorías relacionadas."""
        return self.db.scalar(
            select(Career)
            .options(joinedload(Career.infos).joinedload(CareerInfo.category))
            .where(Career.id == career_id)
        )

    def create(self, career: Career) -> Career:
        """Persiste una carrera nueva."""
        self.db.add(career)
        self.db.commit()
        self.db.refresh(career)
        return career

    def save(self, career: Career) -> Career:
        """Guarda cambios de una carrera existente."""
        self.db.add(career)
        self.db.commit()
        self.db.refresh(career)
        return career

    def delete(self, career: Career) -> None:
        """Elimina una carrera."""
        self.db.delete(career)
        self.db.commit()

    def reorder(self, ordered_ids: list[int]) -> list[Career]:
        """Aplica un nuevo orden según la lista de IDs recibida."""
        all_careers = {
            c.id: c for c in self.db.scalars(select(Career)).all()
        }
        seen: set[int] = set()
        for index, career_id in enumerate(ordered_ids):
            career = all_careers.get(career_id)
            if not career:
                continue
            career.sort_order = index
            self.db.add(career)
            seen.add(career_id)

        remaining = [c for cid, c in all_careers.items() if cid not in seen]
        remaining.sort(key=lambda c: (c.sort_order, c.name))
        for offset, career in enumerate(remaining):
            career.sort_order = len(seen) + offset
            self.db.add(career)

        self.db.commit()
        return self.list_all()
