"""Utilidades para guardar archivos subidos (PDF e imágenes)."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import AppError

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


def ensure_upload_dir() -> Path:
    """Crea el directorio de uploads si no existe."""
    path = Path(get_settings().upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "avatars").mkdir(parents=True, exist_ok=True)
    (path / "documents").mkdir(parents=True, exist_ok=True)
    (path / "branding").mkdir(parents=True, exist_ok=True)
    return path


async def save_upload(
    file: UploadFile,
    subfolder: str = "",
    *,
    allowed_extensions: set[str] | None = None,
    max_size: int | None = None,
) -> str:
    """Guarda un archivo y retorna la URL pública relativa (/static/uploads/...)."""
    ensure_upload_dir()
    allowed = allowed_extensions or ALLOWED_EXTENSIONS
    limit = max_size if max_size is not None else MAX_FILE_SIZE
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise AppError(f"Extensión no permitida: {suffix or '(sin extensión)'}", status_code=400)

    content = await file.read()
    if len(content) > limit:
        raise AppError("El archivo supera el tamaño máximo permitido", status_code=400)

    target_dir = Path(get_settings().upload_dir) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    destination = target_dir / filename
    destination.write_bytes(content)

    relative_parts = ["uploads"]
    if subfolder:
        relative_parts.append(subfolder.strip("/"))
    relative_parts.append(filename)
    return "/static/" + "/".join(relative_parts)


async def save_avatar(file: UploadFile) -> str:
    """Guarda una imagen de perfil en static/uploads/avatars/."""
    return await save_upload(
        file,
        subfolder="avatars",
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        max_size=MAX_AVATAR_SIZE,
    )


async def save_document(file: UploadFile) -> str:
    """Guarda un documento de categoría (.pdf o .png)."""
    return await save_upload(
        file,
        subfolder="documents",
        allowed_extensions=ALLOWED_DOCUMENT_EXTENSIONS,
    )


async def save_branding(file: UploadFile) -> str:
    """Guarda logo de header/footer en static/uploads/branding/."""
    return await save_upload(
        file,
        subfolder="branding",
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        max_size=MAX_AVATAR_SIZE,
    )
