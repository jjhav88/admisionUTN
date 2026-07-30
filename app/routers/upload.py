"""Router de carga de archivos (PDF e imágenes)."""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.dependencies import get_current_user
from app.core.exceptions import AppError
from app.models.user import User
from app.utils.file_upload import save_document, save_upload

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    kind: str | None = Query(default=None, description="Usar 'document' para solo PDF/PNG"),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Recibe un archivo, lo guarda en static/uploads y retorna su URL pública."""
    try:
        if kind == "document":
            url = await save_document(file)
        else:
            url = await save_upload(file)
    except AppError:
        raise
    except Exception as exc:  # pragma: no cover - errores de IO inesperados
        raise AppError(f"No se pudo guardar el archivo: {exc}", status_code=500) from exc

    return {
        "url": url,
        "filename": file.filename or "archivo",
        "uploaded_by": user.username,
    }
