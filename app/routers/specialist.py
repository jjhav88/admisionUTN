"""Router del especialista: consulta de carreras/info y edición con permiso fino."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_specialist_or_admin
from app.models.user import User
from app.schemas.career import CareerRead
from app.schemas.career_info import CareerDetailRead, CareerInfoGrouped, CareerInfoRead, CareerInfoUpdate
from app.schemas.discount import DiscountRead
from app.services.specialist_service import SpecialistService

router = APIRouter(
    prefix="/api/specialist",
    tags=["specialist"],
    dependencies=[Depends(require_specialist_or_admin)],
)


@router.get("/careers", response_model=list[CareerRead])
def list_careers(
    q: str | None = Query(default=None, description="Filtro por nombre"),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Lista carreras disponibles, con filtros opcionales."""
    return SpecialistService(db).list_careers(q=q, active_only=active_only)


@router.get("/careers/{career_id}/info", response_model=CareerDetailRead)
def get_career_info(
    career_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_specialist_or_admin),
):
    """Obtiene toda la información de una carrera agrupada por categoría."""
    return SpecialistService(db).get_career_detail(career_id, user)


@router.get(
    "/careers/{career_id}/info/{category_id}",
    response_model=CareerInfoGrouped,
)
def get_career_category_info(
    career_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_specialist_or_admin),
):
    """Obtiene el contenido de una categoría específica."""
    return SpecialistService(db).get_category_info(career_id, category_id, user)


@router.put(
    "/careers/{career_id}/info/{category_id}",
    response_model=CareerInfoRead,
)
def update_career_category_info(
    career_id: int,
    category_id: int,
    payload: CareerInfoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_specialist_or_admin),
):
    """Edita contenido solo si existe Permission.can_edit=True (admin siempre)."""
    return SpecialistService(db).update_category_info(user, career_id, category_id, payload)


@router.get("/discounts", response_model=list[DiscountRead])
def list_discounts(
    active_only: bool = Query(default=True, description="Si false, retorna todos"),
    db: Session = Depends(get_db),
):
    """Lista descuentos activos (o todos)."""
    return SpecialistService(db).list_discounts(active_only=active_only)
