"""Punto de entrada FastAPI: middlewares, handlers y registro de routers."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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


static_dir = Path(__file__).parent / "app" / "static"
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
