"""Servicio administrativo: carreras, categorías y descuentos."""

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.career import Career, CareerLevel
from app.models.category import Category, CategoryFieldType
from app.models.discount import Discount
from app.repositories.career_repository import CareerRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.discount_repository import DiscountRepository
from app.schemas.career import CareerCreate, CareerUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.discount import DiscountCreate, DiscountUpdate
from app.utils.helpers import slugify


SELECT_FIELD_TYPES = {
    CategoryFieldType.SINGLE_SELECT,
    CategoryFieldType.MULTI_SELECT,
    CategoryFieldType.SELECT_LIST,
}


class AdminService:
    """CRUD de entidades gestionadas por el administrador."""

    def __init__(self, db: Session):
        self.careers = CareerRepository(db)
        self.categories = CategoryRepository(db)
        self.discounts = DiscountRepository(db)

    # --- Careers ---
    def list_careers(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        level: CareerLevel | None = None,
    ) -> list[Career]:
        return self.careers.list_all(search=search, is_active=is_active, level=level)

    def get_career(self, career_id: int) -> Career:
        career = self.careers.get_by_id(career_id)
        if not career:
            raise NotFoundError("Carrera no encontrada")
        return career

    def create_career(self, data: CareerCreate) -> Career:
        slug = slugify(data.name)
        if self.careers.get_by_slug(slug):
            raise ConflictError("Ya existe una carrera con ese nombre/slug")
        career = Career(
            name=data.name,
            slug=slug,
            description=data.description,
            level=data.level,
            is_active=data.is_active,
            sort_order=self.careers.next_sort_order(),
        )
        return self.careers.create(career)

    def update_career(self, career_id: int, data: CareerUpdate) -> Career:
        career = self.get_career(career_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload:
            new_slug = slugify(payload["name"])
            existing = self.careers.get_by_slug(new_slug)
            if existing and existing.id != career.id:
                raise ConflictError("Slug duplicado")
            career.slug = new_slug
        for key, value in payload.items():
            setattr(career, key, value)
        return self.careers.save(career)

    def delete_career(self, career_id: int) -> None:
        career = self.get_career(career_id)
        self.careers.delete(career)

    def reorder_careers(self, ordered_ids: list[int]) -> list[Career]:
        """Reordena carreras según la secuencia de IDs."""
        return self.careers.reorder(ordered_ids)

    # --- Categories ---
    def list_categories(self, search: str | None = None) -> list[Category]:
        return self.categories.list_all(search=search)

    def get_category(self, category_id: int) -> Category:
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("Categoría no encontrada")
        return category

    def create_category(self, data: CategoryCreate) -> Category:
        if self.categories.get_by_name(data.name):
            raise ConflictError("La categoría ya existe")
        self._validate_category_field(data.field_type, data.field_options)
        category = Category(
            name=data.name,
            description=data.description,
            is_editable=data.is_editable,
            allows_document=data.allows_document or data.field_type == CategoryFieldType.FILE,
            field_type=data.field_type,
            field_options=data.field_options,
            sort_order=self.categories.next_sort_order(),
        )
        return self.categories.create(category)

    def update_category(self, category_id: int, data: CategoryUpdate) -> Category:
        category = self.get_category(category_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload:
            existing = self.categories.get_by_name(payload["name"])
            if existing and existing.id != category.id:
                raise ConflictError("La categoría ya existe")

        field_type = payload.get("field_type", category.field_type)
        if "field_options" in payload or "field_type" in payload:
            options = payload.get("field_options", category.field_options)
            self._validate_category_field(field_type, options)
            if field_type not in SELECT_FIELD_TYPES:
                payload["field_options"] = None

        resolved_type = field_type
        if isinstance(resolved_type, str):
            resolved_type = CategoryFieldType(resolved_type)
        if resolved_type == CategoryFieldType.FILE:
            payload["allows_document"] = True

        for key, value in payload.items():
            setattr(category, key, value)
        return self.categories.save(category)

    @staticmethod
    def _validate_category_field(field_type, field_options) -> None:
        if isinstance(field_type, str):
            field_type = CategoryFieldType(field_type)
        options = [str(o).strip() for o in (field_options or []) if str(o).strip()]
        if field_type in SELECT_FIELD_TYPES and len(options) < 2:
            raise AppError("Las categorías de selección requieren al menos 2 opciones")


    def delete_category(self, category_id: int) -> None:
        category = self.get_category(category_id)
        self.categories.delete(category)

    def reorder_categories(self, ordered_ids: list[int]) -> list[Category]:
        """Reordena categorías según la secuencia de IDs."""
        return self.categories.reorder(ordered_ids)

    # --- Discounts ---
    def list_discounts(
        self,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> list[Discount]:
        return self.discounts.list_all(search=search, is_active=is_active)

    def get_discount(self, discount_id: int) -> Discount:
        discount = self.discounts.get_by_id(discount_id)
        if not discount:
            raise NotFoundError("Descuento no encontrado")
        return discount

    def create_discount(self, data: DiscountCreate) -> Discount:
        self.get_career(data.career_id)
        if data.category_id is not None:
            self.get_category(data.category_id)
        self._validate_discount_dates(data.start_date, data.end_date)
        return self.discounts.create(Discount(**data.model_dump()))

    def update_discount(self, discount_id: int, data: DiscountUpdate) -> Discount:
        discount = self.get_discount(discount_id)
        payload = data.model_dump(exclude_unset=True)
        if "career_id" in payload:
            self.get_career(payload["career_id"])
        if "category_id" in payload and payload["category_id"] is not None:
            self.get_category(payload["category_id"])
        start = payload.get("start_date", discount.start_date)
        end = payload.get("end_date", discount.end_date)
        if "end_date" in payload or "start_date" in payload:
            self._validate_discount_dates(start, end)
        for key, value in payload.items():
            setattr(discount, key, value)
        return self.discounts.save(discount)

    def delete_discount(self, discount_id: int) -> None:
        discount = self.get_discount(discount_id)
        self.discounts.delete(discount)

    @staticmethod
    def _validate_discount_dates(start_date, end_date) -> None:
        if start_date and end_date and end_date < start_date:
            raise AppError("La fecha de fin no puede ser anterior a la de inicio")
