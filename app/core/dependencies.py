"""Dependencias FastAPI de autenticación y autorización por roles."""

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _extract_token(
    request: Request,
    bearer: str | None,
    cookie_token: str | None,
) -> str | None:
    """Obtiene el JWT desde Authorization Bearer o cookie HttpOnly."""
    if bearer:
        return bearer
    if cookie_token:
        return cookie_token
    return request.cookies.get(settings.cookie_name)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    bearer: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> User:
    """Valida el token JWT y retorna el usuario autenticado activo."""
    token = _extract_token(request, bearer, cookie_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = UserRepository(db).get_by_id(int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o inexistente",
        )
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    bearer: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> User | None:
    """Igual que get_current_user, pero retorna None si no hay sesión válida."""
    token = _extract_token(request, bearer, cookie_token)
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    user = UserRepository(db).get_by_id(int(user_id))
    if not user or not user.is_active:
        return None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Exige rol admin (verifica user.role.name / valor del enum)."""
    if user.role_name != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol administrador",
        )
    return user


def require_specialist_or_admin(user: User = Depends(get_current_user)) -> User:
    """Exige rol specialist o admin."""
    if user.role_name not in {UserRole.ADMIN.value, UserRole.SPECIALIST.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return user
