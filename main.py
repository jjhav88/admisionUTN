"""Punto de entrada FastAPI: middlewares, handlers y registro de routers."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.exceptions import AppError
from app.core.logging_config import get_logger, setup_logging
from app.core.schema_migrate import ensure_schema
from app.models import Base
from app.routers import admin, auth, specialist, upload, web
from app.utils.file_upload import ensure_upload_dir
from seed import run_seed

settings = get_settings()
setup_logging(settings.debug)
logger = get_logger()


def _wants_login_redirect(request: Request) -> bool:
    """True si es navegación de página (HTML), no llamada a la API JSON."""
    path = request.url.path
    if path.startswith("/api/") or path in {"/health", "/openapi.json", "/docs", "/redoc"}:
        return False
    accept = (request.headers.get("accept") or "").lower()
    # fetch/XHR suelen pedir JSON; el browser al refrescar pide text/html.
    if "application/json" in accept and "text/html" not in accept:
        return False
    return True


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Crea tablas, directorio de uploads y datos seed al iniciar."""
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    ensure_upload_dir()
    db = SessionLocal()
    try:
        run_seed(db)
        logger.info("Aplicación iniciada — seed listo")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Rate limiting (login)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS restringido al frontend configurado
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Convierte errores de dominio en JSON {detail, status_code}."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """En páginas HTML, sesión caducada → login; en API se mantiene JSON."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED and _wants_login_redirect(request):
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(settings.cookie_name)
        return response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers) if exc.headers else None,
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Misma política de redirect para excepciones Starlette (p. ej. 401)."""
    if exc.status_code == 401 and _wants_login_redirect(request):
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(settings.cookie_name)
        return response
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


static_dir = Path(__file__).parent / "app" / "static"
upload_dir = Path(settings.upload_dir)
default_uploads = (static_dir / "uploads").resolve()
# Si UPLOAD_DIR está fuera de app/static/uploads (p. ej. disco /var/data),
# montarlo en /static/uploads para que las URLs de la BD sigan funcionando.
if upload_dir.resolve() != default_uploads:
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/uploads",
        StaticFiles(directory=str(upload_dir)),
        name="uploads",
    )
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(specialist.router)
app.include_router(upload.router)
app.include_router(web.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck simple."""
    return {"status": "ok", "app": settings.app_name}
