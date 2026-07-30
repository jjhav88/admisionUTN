"""Utilidades de seguridad: hashing bcrypt y tokens JWT."""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


def _admin_password_fernet() -> Fernet:
    """Fernet derivado del secret_key para recuperación admin de contraseñas."""
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_password_for_admin(password: str) -> str:
    """Cifra la contraseña para que un admin pueda recuperarla en el panel."""
    return _admin_password_fernet().encrypt(password.encode("utf-8")).decode("utf-8")


def decrypt_password_for_admin(token: str | None) -> str | None:
    """Descifra la contraseña admin; None si no hay valor o es inválido."""
    if not token:
        return None
    try:
        return _admin_password_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Crea un JWT firmado con el subject (normalmente user.id)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """Decodifica un JWT y retorna el subject, o None si es inválido."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        return str(subject) if subject is not None else None
    except JWTError:
        return None
