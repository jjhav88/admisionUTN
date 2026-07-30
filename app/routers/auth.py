"""Router de autenticación: login JWT Bearer y perfil del usuario."""

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logging_config import get_logger
from app.models.user import User
from app.schemas.token import LoginRequest, Token
from app.schemas.user import ProfileUpdate, UserRead
from app.services.auth_service import AuthService
from app.utils.file_upload import save_avatar

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
logger = get_logger("admitomi.auth")
# Activo en producción (DEBUG=false). En desarrollo se desactiva para no frenar tests/UI.
limiter = Limiter(key_func=get_remote_address, enabled=not settings.debug)


def _set_auth_cookie(response: Response, token: str) -> None:
    """Guarda el JWT también en cookie HttpOnly (soporte plantillas)."""
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        secure=not settings.debug,
    )


@router.post("/login", response_model=Token)
@limiter.limit(settings.login_rate_limit)
def login_form(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Inicia sesión (OAuth2 password flow) y retorna access_token JWT."""
    service = AuthService(db)
    user = service.authenticate(form_data.username, form_data.password)
    token = service.create_token_for_user(user)
    _set_auth_cookie(response, token)
    logger.info("login ok user=%s role=%s", user.username, user.role_name)
    return Token(access_token=token)


@router.post("/login/json", response_model=Token)
@limiter.limit(settings.login_rate_limit)
def login_json(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> Token:
    """Login JSON para el frontend (localStorage + Authorization Bearer)."""
    service = AuthService(db)
    user = service.authenticate(payload.username, payload.password)
    token = service.create_token_for_user(user)
    _set_auth_cookie(response, token)
    logger.info("login json ok user=%s", user.username)
    return Token(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Cierra sesión eliminando la cookie de acceso."""
    response.delete_cookie(settings.cookie_name)
    return {"detail": "Sesión cerrada"}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    """Retorna el perfil del usuario autenticado."""
    return user


@router.put("/me", response_model=UserRead)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """Actualiza datos del propio perfil (nombre, email, usuario, contraseña)."""
    updated = AuthService(db).update_profile(user, payload)
    logger.info("profile updated user=%s", updated.username)
    return updated


@router.post("/me/avatar", response_model=UserRead)
async def update_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """Sube o reemplaza la foto de perfil del usuario autenticado."""
    url = await save_avatar(file)
    return AuthService(db).set_avatar(user.id, url)
