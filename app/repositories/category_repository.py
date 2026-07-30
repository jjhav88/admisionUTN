"""Repositorio de acceso a datos para categorías."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    """Operaciones CRUD y consultas de Category."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.db.scalar(select(Category).where(Category.name == name))

    def list_all(self, search: str | None = None) -> list[Category]:
        """Lista categorías ordenadas por sort_order, con búsqueda opcional."""
        stmt = select(Category).order_by(Category.sort_order, Category.name)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Category.name.ilike(term),
                    Category.description.ilike(term),
                )
            )
        return list(self.db.scalars(stmt).all())

    def next_sort_order(self) -> int:
        """Calcula el siguiente sort_order al crear una categoría."""
        current = self.db.scalar(select(func.max(Category.sort_order)))
        return int(current or 0) + 1

    def create(self, category: Category) -> Category:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def save(self, category: Category) -> Category:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.commit()

    def reorder(self, ordered_ids: list[int]) -> list[Category]:
        """Aplica un nuevo orden según la lista de IDs recibida."""
        all_categories = {
            c.id: c for c in self.db.scalars(select(Category)).all()
        }
        seen: set[int] = set()
        for index, category_id in enumerate(ordered_ids):
            category = all_categories.get(category_id)
            if not category:
                continue
            category.sort_order = index
            self.db.add(category)
            seen.add(category_id)

        remaining = [c for cid, c in all_categories.items() if cid not in seen]
        remaining.sort(key=lambda c: (c.sort_order, c.name))
        for offset, category in enumerate(remaining):
            category.sort_order = len(seen) + offset
            self.db.add(category)

        self.db.commit()
        return self.list_all()
