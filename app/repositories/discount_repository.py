"""Repositorio de acceso a datos para descuentos."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.career import Career
from app.models.category import Category
from app.models.discount import Discount


class DiscountRepository:
    """Operaciones CRUD y consultas de Discount."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, discount_id: int) -> Discount | None:
        """Obtiene un descuento por id con relaciones."""
        return self.db.scalar(
            select(Discount)
            .options(joinedload(Discount.career), joinedload(Discount.category))
            .where(Discount.id == discount_id)
        )

    def list_all(
        self,
        active_only: bool = False,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> list[Discount]:
        """Lista descuentos con búsqueda y filtro de estado."""
        stmt = (
            select(Discount)
            .options(joinedload(Discount.career), joinedload(Discount.category))
            .outerjoin(Career, Discount.career_id == Career.id)
            .outerjoin(Category, Discount.category_id == Category.id)
            .order_by(Discount.id.desc())
        )
        if active_only or is_active is True:
            stmt = stmt.where(Discount.is_active.is_(True))
        elif is_active is False:
            stmt = stmt.where(Discount.is_active.is_(False))
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Discount.title.ilike(term),
                    Discount.description.ilike(term),
                    Career.name.ilike(term),
                    Category.name.ilike(term),
                )
            )
        return list(self.db.scalars(stmt).unique().all())

    def list_by_career(self, career_id: int) -> list[Discount]:
        """Lista descuentos de una carrera."""
        return list(
            self.db.scalars(
                select(Discount).where(Discount.career_id == career_id).order_by(Discount.id.desc())
            ).all()
        )

    def create(self, discount: Discount) -> Discount:
        """Crea un descuento."""
        self.db.add(discount)
        self.db.commit()
        self.db.refresh(discount)
        return self.get_by_id(discount.id) or discount

    def save(self, discount: Discount) -> Discount:
        """Actualiza un descuento."""
        self.db.add(discount)
        self.db.commit()
        self.db.refresh(discount)
        return self.get_by_id(discount.id) or discount

    def delete(self, discount: Discount) -> None:
        """Elimina un descuento."""
        self.db.delete(discount)
        self.db.commit()
