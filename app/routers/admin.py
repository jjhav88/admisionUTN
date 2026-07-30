"""Router de administración: CRUD de usuarios, carreras, categorías, permisos y descuentos."""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User, UserRole
from app.models.career import CareerLevel
from app.schemas.career import CareerCreate, CareerRead, CareerReorder, CareerUpdate
from app.schemas.category import CategoryCreate, CategoryRead, CategoryReorder, CategoryUpdate
from app.schemas.discount import DiscountCreate, DiscountRead, DiscountUpdate
from app.schemas.permission import PermissionBulkCreate, PermissionCreate, PermissionRead
from app.schemas.site_settings import SiteSettingsRead, SiteSettingsUpdate
from app.schemas.user import UserAdminRead, UserCreate, UserRead, UserUpdate
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.site_settings_service import SiteSettingsService
from app.utils.file_upload import restore_upload, save_avatar, save_branding

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# --- Users ---
@router.get("/users", response_model=list[UserRead])
def list_users(
    q: str | None = Query(default=None, description="Buscar por usuario, email o nombre"),
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[User]:
    """Lista usuarios con búsqueda y filtros."""
    return AuthService(db).list_users(search=q, role=role, is_active=is_active)


@router.get("/users/{user_id}", response_model=UserAdminRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserAdminRead:
    """Obtiene un usuario por id (incluye contraseña para el panel admin)."""
    service = AuthService(db)
    return service.to_admin_read(service.get_user(user_id))


@router.post("/users", response_model=UserAdminRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserAdminRead:
    """Crea un usuario (típicamente especialista)."""
    service = AuthService(db)
    return service.to_admin_read(service.create_user(payload))


@router.put("/users/{user_id}", response_model=UserAdminRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> UserAdminRead:
    """Edita un usuario existente."""
    service = AuthService(db)
    return service.to_admin_read(service.update_user(user_id, payload, actor=actor))


@router.post("/users/{user_id}/avatar", response_model=UserRead)
async def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> User:
    """Sube o reemplaza la foto de perfil del usuario."""
    url = await save_avatar(file)
    return AuthService(db).set_avatar(user_id, url)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> None:
    """Elimina un usuario."""
    AuthService(db).delete_user(user_id, actor=actor)


# --- Careers ---
@router.get("/careers", response_model=list[CareerRead])
def list_careers(
    q: str | None = Query(default=None, description="Buscar por nombre, slug o descripción"),
    is_active: bool | None = Query(default=None),
    level: CareerLevel | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista carreras con búsqueda y filtros."""
    return AdminService(db).list_careers(search=q, is_active=is_active, level=level)


@router.post("/careers", response_model=CareerRead, status_code=201)
def create_career(payload: CareerCreate, db: Session = Depends(get_db)):
    """Crea una carrera."""
    return AdminService(db).create_career(payload)


@router.put("/careers/reorder", response_model=list[CareerRead])
def reorder_careers(payload: CareerReorder, db: Session = Depends(get_db)):
    """Reordena carreras arrastrando paneles en la UI."""
    return AdminService(db).reorder_careers(payload.ids)


@router.put("/careers/{career_id}", response_model=CareerRead)
def update_career(career_id: int, payload: CareerUpdate, db: Session = Depends(get_db)):
    """Edita una carrera."""
    return AdminService(db).update_career(career_id, payload)


@router.delete("/careers/{career_id}", status_code=204)
def delete_career(career_id: int, db: Session = Depends(get_db)) -> None:
    """Elimina una carrera."""
    AdminService(db).delete_career(career_id)


# --- Categories ---
@router.get("/categories", response_model=list[CategoryRead])
def list_categories(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista categorías dinámicas."""
    return AdminService(db).list_categories(search=q)


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    """Crea una categoría."""
    return AdminService(db).create_category(payload)


@router.put("/categories/reorder", response_model=list[CategoryRead])
def reorder_categories(payload: CategoryReorder, db: Session = Depends(get_db)):
    """Reordena categorías por lista de IDs."""
    return AdminService(db).reorder_categories(payload.ids)


@router.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    """Edita una categoría."""
    return AdminService(db).update_category(category_id, payload)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    """Elimina una categoría."""
    AdminService(db).delete_category(category_id)


# --- Discounts ---
@router.get("/discounts", response_model=list[DiscountRead])
def list_discounts(
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lista descuentos."""
    return AdminService(db).list_discounts(search=q, is_active=is_active)


@router.post("/discounts", response_model=DiscountRead, status_code=201)
def create_discount(payload: DiscountCreate, db: Session = Depends(get_db)):
    """Crea un descuento."""
    return AdminService(db).create_discount(payload)


@router.put("/discounts/{discount_id}", response_model=DiscountRead)
def update_discount(discount_id: int, payload: DiscountUpdate, db: Session = Depends(get_db)):
    """Edita un descuento."""
    return AdminService(db).update_discount(discount_id, payload)


@router.delete("/discounts/{discount_id}", status_code=204)
def delete_discount(discount_id: int, db: Session = Depends(get_db)) -> None:
    """Elimina un descuento."""
    AdminService(db).delete_discount(discount_id)


# --- Permissions ---
@router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(db: Session = Depends(get_db)):
    """Lista permisos granulares."""
    return PermissionService(db).list_all()


@router.post("/permissions", response_model=PermissionRead, status_code=201)
def create_permission(payload: PermissionCreate, db: Session = Depends(get_db)):
    """Asigna permiso de edición a un especialista."""
    return PermissionService(db).create(payload)


@router.post("/permissions/bulk", response_model=list[PermissionRead], status_code=201)
def create_permissions_bulk(payload: PermissionBulkCreate, db: Session = Depends(get_db)):
    """Asigna permisos para cada combinación de categorías y carreras."""
    return PermissionService(db).create_bulk(payload)


@router.delete("/permissions/{permission_id}", status_code=204)
def delete_permission(permission_id: int, db: Session = Depends(get_db)) -> None:
    """Revoca un permiso."""
    PermissionService(db).delete(permission_id)


# --- Site settings ---
@router.get("/settings", response_model=SiteSettingsRead)
def get_site_settings(db: Session = Depends(get_db)):
    """Obtiene la configuración del header/footer."""
    return SiteSettingsService(db).get_or_create()


@router.put("/settings", response_model=SiteSettingsRead)
def update_site_settings(payload: SiteSettingsUpdate, db: Session = Depends(get_db)):
    """Actualiza textos de header, footer y contacto."""
    return SiteSettingsService(db).update(payload)


@router.post("/settings/header-logo", response_model=SiteSettingsRead)
async def upload_header_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube el logo del header."""
    url = await save_branding(file)
    return SiteSettingsService(db).set_header_logo(url)


@router.post("/settings/footer-logo", response_model=SiteSettingsRead)
async def upload_footer_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube el escudo/logo del footer."""
    url = await save_branding(file)
    return SiteSettingsService(db).set_footer_logo(url)


@router.post("/restore-upload")
async def restore_uploaded_file(
    relative_path: str = Query(..., description="Ruta relativa, ej. avatars/abc.jpeg"),
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Restaura un archivo local con el mismo nombre (migración de uploads a Render)."""
    url = await restore_upload(relative_path, file)
    return {"url": url, "relative_path": relative_path}
