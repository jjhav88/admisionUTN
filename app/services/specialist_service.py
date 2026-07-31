"""Servicio del especialista: consulta y edición condicional de información."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.career import Career, CareerLevel
from app.models.career_info import CareerInfo
from app.models.discount import Discount
from app.models.user import User
from app.repositories.career_info_repository import CareerInfoRepository
from app.repositories.career_repository import CareerRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.discount_repository import DiscountRepository
from app.schemas.career_info import CareerDetailRead, CareerInfoGrouped, CareerInfoUpdate
from app.services.permission_service import PermissionService
from app.utils.sanitize import is_empty_rich_text, sanitize_html, strip_html_to_text


class SpecialistService:
    """Lógica de negocio para el rol specialist (y admin en lectura/edición)."""

    def __init__(self, db: Session):
        self.careers = CareerRepository(db)
        self.categories = CategoryRepository(db)
        self.infos = CareerInfoRepository(db)
        self.discounts = DiscountRepository(db)
        self.permissions = PermissionService(db)

    def list_careers(
        self,
        q: str | None = None,
        active_only: bool = True,
        level: CareerLevel | None = None,
    ) -> list[Career]:
        """Lista carreras con filtro opcional por nombre y nivel académico."""
        return self.careers.list_all(active_only=active_only, search=q, level=level)

    def dashboard_summary(self, user: User) -> dict:
        """Resumen de métricas para el panel del especialista."""
        careers = self.list_careers()
        perms = [p for p in self.permissions.list_for_user(user.id) if p.can_edit]
        return {
            "careers_count": len(careers),
            "editable_careers_count": len({p.career_id for p in perms}),
            "editable_categories_count": len({p.category_id for p in perms}),
            "discounts_count": len(self.list_discounts(active_only=True)),
        }

    def get_career_detail(
        self,
        career_id: int,
        user: User,
        *,
        include_inactive: bool = False,
    ) -> CareerDetailRead:
        """Obtiene la carrera con info agrupada por categoría e indica can_edit."""
        career = self.careers.get_by_id(career_id)
        if not career:
            raise NotFoundError("Carrera no encontrada")
        if not career.is_active and not include_inactive:
            raise NotFoundError("Carrera no encontrada")

        infos = {info.category_id: info for info in self.infos.list_by_career(career_id)}
        grouped: list[CareerInfoGrouped] = []
        for category in self.categories.list_all():
            info = infos.get(category.id)
            extra = info.extra_data if info else None
            field_type = (
                category.field_type.value
                if hasattr(category.field_type, "value")
                else str(category.field_type or "long_text")
            )
            raw_content = info.content if info else None
            content = self._display_content(raw_content, field_type)
            grouped.append(
                CareerInfoGrouped(
                    category_id=category.id,
                    category_name=category.name,
                    content=content,
                    extra_data=extra,
                    sort_order=info.sort_order if info else category.sort_order,
                    can_edit=self.permissions.can_edit(user, career_id, category.id),
                    allows_document=bool(category.allows_document) or field_type == "file",
                    field_type=field_type,
                    field_options=category.options_list,
                    selected_values=self._selected_values(content, extra),
                    info_id=info.id if info else None,
                    updated_at=info.updated_at if info else None,
                )
            )

        level_value = career.level.value if hasattr(career.level, "value") else str(career.level)
        return CareerDetailRead(
            id=career.id,
            name=career.name,
            slug=career.slug,
            description=career.description,
            level=level_value,
            categories=grouped,
        )

    def get_category_info(self, career_id: int, category_id: int, user: User) -> CareerInfoGrouped:
        """Obtiene el contenido de una categoría específica de la carrera."""
        detail = self.get_career_detail(career_id, user)
        for item in detail.categories:
            if item.category_id == category_id:
                return item
        raise NotFoundError("Categoría no encontrada en la carrera")

    def update_category_info(
        self,
        user: User,
        career_id: int,
        category_id: int,
        data: CareerInfoUpdate,
    ) -> CareerInfo:
        """Edita (o crea) contenido si el usuario tiene Permission.can_edit=True."""
        career = self.careers.get_by_id(career_id)
        if not career:
            raise NotFoundError("Carrera no encontrada")
        category = self.categories.get_by_id(category_id)
        if not category:
            raise NotFoundError("Categoría no encontrada")

        self.permissions.require_edit(user, career_id, category_id)

        payload = data.model_dump(exclude_unset=True)
        if "content" in payload:
            payload["content"] = self._normalize_content(payload["content"], category.field_type)

        if "extra_data" in payload and payload["extra_data"] is not None:
            extra = dict(payload["extra_data"])
            field_type = (
                category.field_type.value
                if hasattr(category.field_type, "value")
                else str(category.field_type or "long_text")
            )
            allows_file = bool(category.allows_document) or field_type == "file"
            if not allows_file:
                extra.pop("document_url", None)
                extra.pop("document_name", None)
            if "selected" in extra and isinstance(extra["selected"], str):
                extra["selected"] = strip_html_to_text(extra["selected"]) or None
            if "items" in extra:
                raw_items = extra.get("items")
                if isinstance(raw_items, list):
                    cleaned_items = [
                        strip_html_to_text(item)
                        for item in raw_items
                        if strip_html_to_text(item)
                    ]
                    if cleaned_items:
                        extra["items"] = cleaned_items
                    else:
                        extra.pop("items", None)
                else:
                    extra.pop("items", None)
            if extra.get("schedule") is None:
                extra.pop("schedule", None)
            payload["extra_data"] = extra or None

        existing = self.infos.get_by_career_and_category(career_id, category_id)
        if existing:
            if "extra_data" in payload and payload["extra_data"] is not None and existing.extra_data:
                merged = dict(existing.extra_data)
                merged.update(payload["extra_data"])
                if payload["extra_data"].get("document_url") is None:
                    merged.pop("document_url", None)
                    merged.pop("document_name", None)
                if "schedule" in payload["extra_data"] and payload["extra_data"].get("schedule") is None:
                    merged.pop("schedule", None)
                payload["extra_data"] = merged or None
            for key, value in payload.items():
                setattr(existing, key, value)
            return self.infos.save(existing)

        return self.infos.create(
            CareerInfo(
                career_id=career_id,
                category_id=category_id,
                content=payload.get("content"),
                extra_data=payload.get("extra_data"),
                sort_order=payload.get("sort_order", category.sort_order),
            )
        )

    @staticmethod
    def _display_content(content: str | None, field_type: str) -> str | None:
        """Prepara el contenido para UI según el tipo de campo."""
        if content is None:
            return None
        if field_type == "long_text":
            return None if is_empty_rich_text(content) else content
        plain = strip_html_to_text(content)
        return plain or None

    @staticmethod
    def _normalize_content(content: str | None, field_type) -> str | None:
        """Normaliza el contenido al guardar según el tipo de categoría."""
        from app.models.category import CategoryFieldType

        if isinstance(field_type, str):
            try:
                field_type = CategoryFieldType(field_type)
            except ValueError:
                field_type = CategoryFieldType.LONG_TEXT

        if (field_type == CategoryFieldType.LONG_TEXT):
            cleaned = sanitize_html(content)
            return None if is_empty_rich_text(cleaned) else cleaned

        if field_type == CategoryFieldType.WEEKDAY_HOURS:
            plain = strip_html_to_text(content)
            return plain or None

        plain = strip_html_to_text(content)
        return plain or None

    @staticmethod
    def _selected_values(content: str | None, extra: dict | None) -> list[str]:
        """Normaliza valores elegidos, lista de elementos o selección."""
        if extra and isinstance(extra.get("items"), list):
            return [
                strip_html_to_text(item)
                for item in extra["items"]
                if strip_html_to_text(item)
            ]
        if extra and "selected" in extra:
            value = extra.get("selected")
            if isinstance(value, list):
                return [strip_html_to_text(item) for item in value if strip_html_to_text(item)]
            if value is None or value == "":
                return []
            plain = strip_html_to_text(value)
            return [plain] if plain else []
        if content and content.strip():
            if "\n" in content:
                return [part.strip() for part in content.splitlines() if part.strip()]
            return [part.strip() for part in content.split(",") if part.strip()]
        return []

    def list_discounts(self, active_only: bool = True) -> list[Discount]:
        """Lista descuentos visibles para el especialista."""
        return self.discounts.list_all(active_only=active_only)
