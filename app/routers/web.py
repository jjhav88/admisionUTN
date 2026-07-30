"""Router web: renderiza plantillas Jinja2 (SSR) para admin y specialist."""

import json

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional, require_admin
from app.models.user import User, UserRole
from app.models.career import CareerLevel
from app.models.category import CategoryFieldType
from app.core.database import SessionLocal
from app.services.admin_service import AdminService
from app.services.auth_service import AuthService
from app.services.permission_service import PermissionService
from app.services.site_settings_service import SiteSettingsService
from app.services.specialist_service import SpecialistService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()
CAREER_LEVELS = list(CareerLevel)
CATEGORY_FIELD_TYPES = list(CategoryFieldType)


def render(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    """Helper para TemplateResponse con app_name y site settings inyectados."""
    data = {"app_name": settings.app_name, **(context or {})}
    if "site" not in data:
        db = SessionLocal()
        try:
            data["site"] = SiteSettingsService(db).get_or_create()
        finally:
            db.close()
    return templates.TemplateResponse(request, name, data, status_code=status_code)


def _redirect_home(user: User) -> RedirectResponse:
    """Redirige al dashboard según rol."""
    if user.role_name == UserRole.ADMIN.value:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/specialist", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user: User | None = Depends(get_current_user_optional)):
    """Raíz: redirige a login o panel."""
    if user:
        return _redirect_home(user)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    """Página de login (el submit real lo hace main.js vía API)."""
    if user:
        return _redirect_home(user)
    return render(request, "auth/login.html", {"error": None})


@router.get("/logout")
def logout():
    """Limpia cookie y redirige a login (también se limpia localStorage en JS)."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.cookie_name)
    return response


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Página para editar el propio perfil (datos + foto)."""
    return render(request, "auth/profile.html", {"user": user})


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Dashboard administrador con conteos."""
    admin = AdminService(db)
    return render(
        request,
        "admin/dashboard.html",
        {
            "user": user,
            "careers_count": len(admin.list_careers()),
            "categories_count": len(admin.list_categories()),
            "users_count": len(AuthService(db).list_users()),
            "discounts_count": len(admin.list_discounts()),
        },
    )


@router.get("/admin/careers", response_class=HTMLResponse)
def admin_careers(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Listado de carreras (CRUD vía API + JS)."""
    return render(
        request,
        "admin/careers.html",
        {"user": user, "careers": AdminService(db).list_careers(), "levels": CAREER_LEVELS},
    )


@router.get("/admin/careers/new", response_class=HTMLResponse)
def admin_career_form(request: Request, user: User = Depends(require_admin)):
    """Formulario de alta de carrera."""
    return render(
        request,
        "admin/career_form.html",
        {"user": user, "career": None, "levels": CAREER_LEVELS},
    )


@router.get("/admin/careers/{career_id}/edit", response_class=HTMLResponse)
def admin_career_edit(
    career_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Formulario de edición de carrera."""
    career = AdminService(db).get_career(career_id)
    return render(
        request,
        "admin/career_form.html",
        {"user": user, "career": career, "levels": CAREER_LEVELS},
    )


@router.get("/admin/careers/{career_id}/info", response_class=HTMLResponse)
def admin_career_info(
    career_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Formulario para registrar información de todas las categorías de una carrera."""
    AdminService(db).get_career(career_id)
    detail = SpecialistService(db).get_career_detail(career_id, user, include_inactive=True)
    return render(
        request,
        "admin/career_info_register.html",
        {"user": user, "detail": detail},
    )

@router.get("/admin/categories", response_class=HTMLResponse)
def admin_categories(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Listado de categorías con reorder."""
    return render(
        request,
        "admin/categories.html",
        {"user": user, "categories": AdminService(db).list_categories()},
    )


@router.get("/admin/categories/new", response_class=HTMLResponse)
def admin_category_form(request: Request, user: User = Depends(require_admin)):
    """Formulario de alta de categoría."""
    return render(
        request,
        "admin/category_form.html",
        {"user": user, "category": None, "field_types": CATEGORY_FIELD_TYPES},
    )


@router.get("/admin/categories/{category_id}/edit", response_class=HTMLResponse)
def admin_category_edit(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Formulario de edición de categoría."""
    category = AdminService(db).get_category(category_id)
    return render(
        request,
        "admin/category_form.html",
        {"user": user, "category": category, "field_types": CATEGORY_FIELD_TYPES},
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Gestión de usuarios."""
    return render(
        request,
        "admin/users.html",
        {"user": user, "users": AuthService(db).list_users(), "roles": list(UserRole)},
    )


@router.get("/admin/permissions", response_class=HTMLResponse)
def admin_permissions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Asignación de permisos finos."""
    admin = AdminService(db)
    specialists = [
        u for u in AuthService(db).list_users() if u.role_name == UserRole.SPECIALIST.value
    ]
    careers = admin.list_careers()
    categories = admin.list_categories()
    permissions = PermissionService(db).list_all()
    return render(
        request,
        "admin/permissions.html",
        {
            "user": user,
            "permissions": permissions,
            "users": specialists,
            "careers": careers,
            "categories": categories,
            "permissions_json": json.dumps(
                [
                    {
                        "user_id": p.user_id,
                        "career_id": p.career_id,
                        "category_id": p.category_id,
                        "can_edit": bool(p.can_edit),
                    }
                    for p in permissions
                ]
            ),
            "careers_json": json.dumps(
                [
                    {
                        "id": c.id,
                        "name": c.name,
                        "level": c.level_label,
                    }
                    for c in careers
                ]
            ),
            "categories_json": json.dumps(
                [{"id": c.id, "name": c.name} for c in categories]
            ),
        },
    )


@router.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Configuración de header y footer."""
    site = SiteSettingsService(db).get_or_create()
    return render(
        request,
        "admin/settings.html",
        {"user": user, "site": site},
    )


@router.get("/admin/discounts", response_class=HTMLResponse)
def admin_discounts(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Listado de descuentos."""
    admin = AdminService(db)
    return render(
        request,
        "admin/discounts.html",
        {
            "user": user,
            "discounts": admin.list_discounts(),
        },
    )


@router.get("/admin/discounts/new", response_class=HTMLResponse)
def admin_discount_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Formulario de alta de descuento."""
    admin = AdminService(db)
    return render(
        request,
        "admin/discount_form.html",
        {
            "user": user,
            "discount": None,
            "careers": admin.list_careers(),
            "categories": admin.list_categories(),
        },
    )


@router.get("/admin/discounts/{discount_id}/edit", response_class=HTMLResponse)
def admin_discount_edit(
    discount_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Formulario de edición de descuento."""
    admin = AdminService(db)
    return render(
        request,
        "admin/discount_form.html",
        {
            "user": user,
            "discount": admin.get_discount(discount_id),
            "careers": admin.list_careers(),
            "categories": admin.list_categories(),
        },
    )


@router.get("/specialist", response_class=HTMLResponse)
def specialist_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard del especialista."""
    if user.role_name == UserRole.ADMIN.value:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    service = SpecialistService(db)
    summary = service.dashboard_summary(user)
    return render(
        request,
        "specialist/dashboard.html",
        {
            "user": user,
            "careers": service.list_careers(),
            **summary,
        },
    )


@router.get("/specialist/careers/{career_id}", response_class=HTMLResponse)
def specialist_career_detail(
    career_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Detalle de carrera (también se puede hidratar vía API)."""
    detail = SpecialistService(db).get_career_detail(career_id, user)
    editable_count = sum(1 for item in detail.categories if item.can_edit)
    return render(
        request,
        "specialist/career_detail.html",
        {"user": user, "detail": detail, "editable_count": editable_count},
    )


@router.get("/specialist/careers/{career_id}/info/{category_id}/edit", response_class=HTMLResponse)
def specialist_info_edit(
    career_id: int,
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Editor de contenido de categoría (Quill + upload vía JS/API)."""
    PermissionService(db).require_edit(user, career_id, category_id)
    info = SpecialistService(db).get_category_info(career_id, category_id, user)
    return render(
        request,
        "specialist/career_info_edit.html",
        {"user": user, "career_id": career_id, "info": info},
    )
