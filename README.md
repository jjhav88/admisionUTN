# AdmiTomi

Sistema web de admisión con FastAPI (MVC/MTV), roles admin/especialista, categorías dinámicas y permisos granulares.

## Stack

- FastAPI + Jinja2 + CSS/JS
- SQLAlchemy 2 + SQLite (dev) / PostgreSQL (prod)
- JWT en cookie HttpOnly + Bearer API
- Gunicorn + Docker + Render

## Arranque rápido (local)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
copy .env.example .env   # o cp .env.example .env
uvicorn main:app --reload
```

Abre `http://127.0.0.1:8000`

### Usuario inicial

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | valor de `ADMIN_PASSWORD` (por defecto `admin123`) | Administrador |

Cambia `ADMIN_PASSWORD` antes de subir a producción. Los especialistas se crean desde **Admin → Usuarios**.

## Docker

```bash
docker compose up --build
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Deploy en Render (piloto)

1. Sube el repo a GitHub.
2. En [Render](https://render.com): **New → Blueprint** y selecciona este repositorio (`render.yaml`),  
   o crea un **Web Service** + **PostgreSQL** manualmente.
3. Variables importantes:
   - `SECRET_KEY` — aleatorio (≥ 32 caracteres); Render puede generarlo.
   - `DEBUG=false`
   - `DATABASE_URL` — la del Postgres de Render.
   - `ADMIN_PASSWORD` — contraseña inicial del admin (cámbiala).
   - `CORS_ORIGINS` — URL pública del servicio, ej. `https://admitomi.onrender.com`
   - `UPLOAD_DIR=/var/data/uploads` — si usas disco persistente.
4. Healthcheck: `GET /health`
5. Tras el primer deploy, inicia sesión, cambia la contraseña del admin y configura **Settings** (logos/contacto).

### Nota sobre archivos

Los uploads (avatars, documentos, logos) viven en disco. En Render el filesystem efímero se pierde en redeploy salvo que montes un **Disk** (incluido en `render.yaml`).

### Seguridad (piloto)

- Con `DEBUG=false` se ocultan `/docs` y `/redoc`.
- No uses `SECRET_KEY` de desarrollo en producción.
- El panel admin puede mostrar contraseñas recuperables cifradas con `SECRET_KEY`; protege ese secreto.

## API (resumen)

- `POST /api/auth/login` — OAuth2 password form
- `POST /api/auth/login/json` — login JSON
- `GET /api/auth/me`
- `/api/admin/...` — CRUD admin
- `/api/specialist/...` — consulta/edición con permisos
- `POST /api/upload` — subida de archivos

## Estructura

```
app/
  core/ models/ schemas/ repositories/ services/ routers/
  templates/ static/ utils/
main.py
seed.py
Procfile
render.yaml
Dockerfile
```
