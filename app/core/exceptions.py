"""Excepciones de dominio independientes de FastAPI.

Los servicios lanzan estas excepciones; los routers/handlers las convierten en HTTP.
"""


class AppError(Exception):
    """Error de aplicación con código HTTP y mensaje legible."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnauthorizedError(AppError):
    """Credenciales inválidas o sesión inexistente."""

    def __init__(self, message: str = "No autenticado"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    """Usuario autenticado sin permiso suficiente."""

    def __init__(self, message: str = "Acceso denegado"):
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    """Recurso no encontrado."""

    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    """Conflicto de unicidad o estado inconsistente."""

    def __init__(self, message: str = "Conflicto de datos"):
        super().__init__(message, status_code=409)
