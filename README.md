# AdmiTomi

**Sistema de Gestión de Información para Admisiones** — plataforma web para centralizar, organizar y publicar la información académica de programas educativos, con control de acceso por roles y permisos granulares.

Orientado a equipos de admisión: administración del catálogo (carreras, categorías, descuentos) y consulta/edición controlada por especialistas.

---

## Descripción del sistema

AdmiTomi permite:

- **Administrar carreras** (nivel académico, orden, estado activo).
- **Definir categorías dinámicas** de información (texto, selección, horarios, archivos, listas, etc.).
- **Registrar el contenido** de cada carrera por categoría.
- **Asignar permisos** a especialistas (usuario × carrera × categoría).
- **Gestionar descuentos** asociados a carrera y categoría.
- **Personalizar branding** (logo de header, escudo de footer y datos de contacto).

Los **especialistas** consultan un panel con las carreras disponibles y un informe tipo documento; solo pueden editar las categorías para las que tienen permiso.

---

## Roles

| Rol | Capacidad principal |
|-----|---------------------|
| **Administrador** | CRUD de usuarios, carreras, categorías, permisos, descuentos y settings del sitio |
| **Especialista** | Consulta de carreras e informe; edición solo donde tenga permiso |

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI |
| Plantillas / UI | Jinja2 + CSS/JS |
| ORM / BD | SQLAlchemy 2 · SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (cookie HttpOnly + Bearer) |
| Servidor | Uvicorn / Gunicorn |
| Contenedores | Docker · Docker Compose |
| Deploy piloto | Render (`render.yaml`) |

---

## Arquitectura

El proyecto sigue una separación en capas (estilo MVC/MTV):

```text
┌─────────────────────────────────────────────────────────┐
│  Cliente (navegador)                                    │
│  Plantillas Jinja2 · CSS/JS · formularios API           │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────┐
│  Routers (FastAPI)                                      │
│  web · auth · admin · specialist · upload               │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Services (lógica de negocio)                           │
│  Auth · Admin · Specialist · Permissions · Settings     │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Repositories + Models (SQLAlchemy)                     │
│  User · Career · Category · CareerInfo · Permission …   │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  Base de datos (SQLite / PostgreSQL)                    │
└─────────────────────────────────────────────────────────┘
```

### Capas principales

| Carpeta | Responsabilidad |
|---------|-----------------|
| `app/routers/` | Endpoints HTTP y páginas SSR |
| `app/services/` | Reglas de negocio y orquestación |
| `app/repositories/` | Acceso a datos |
| `app/models/` | Entidades SQLAlchemy |
| `app/schemas/` | Contratos Pydantic (API) |
| `app/templates/` | Vistas HTML (admin, especialista, auth) |
| `app/static/` | CSS, JS e imágenes |
| `app/core/` | Config, seguridad, DB, dependencias |
| `app/utils/` | Uploads, sanitización HTML |

### Flujo de permisos

```
Admin asigna permiso
    → (usuario, carrera, categoría, can_edit)
        → Especialista ve informe de la carrera
            → Solo categorías con can_edit muestran “Editar”
```

### Módulos funcionales

1. **Autenticación** — login, sesión JWT, perfil.
2. **Carreras** — alta/edición/reordenamiento.
3. **Categorías** — tipos de campo configurables.
4. **Información de carrera** — contenido por categoría (admin o especialista).
5. **Permisos** — asignación y consulta por usuario/carrera.
6. **Descuentos** — vigencia y vínculo a carrera/categoría.
7. **Settings** — logos y contacto del sitio (header/footer).

---

## Estructura del repositorio

```
admitomi/
├── app/
│   ├── core/           # config, DB, JWT, dependencias
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── routers/
│   ├── templates/
│   ├── static/
│   └── utils/
├── tests/
├── alembic/
├── main.py             # entrada FastAPI
├── seed.py             # datos iniciales controlados
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── render.yaml
└── .env.example        # variables de entorno (sin secretos reales)
```

---

## Arranque local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env   # en Windows: copy .env.example .env
uvicorn main:app --reload
```

Aplicación: `http://127.0.0.1:8000`

Configura las variables en `.env` a partir de `.env.example` (nunca subas `.env` al repositorio).

### Docker

```bash
docker compose up --build
```

### Pruebas

```bash
pytest -q
```

---

## Despliegue (piloto)

El repositorio incluye `Procfile` y `render.yaml` para un despliegue tipo **Web Service + PostgreSQL**.

Requisitos generales de producción:

- Base de datos PostgreSQL
- `SECRET_KEY` fuerte y único
- `DEBUG=false`
- `CORS_ORIGINS` con la URL pública del servicio
- Almacenamiento persistente para uploads (disco o equivalente)

Consulta `.env.example` y `render.yaml` para el detalle de variables (sin valores secretos en este documento).

Healthcheck: `GET /health`

---

## API (vista general)

| Área | Prefijo | Uso |
|------|---------|-----|
| Auth | `/api/auth` | Login, perfil, avatar |
| Admin | `/api/admin` | Usuarios, carreras, categorías, permisos, descuentos, settings |
| Especialista | `/api/specialist` | Carreras e información editable |
| Upload | `/api/upload` | Archivos (imágenes/documentos) |
| Web | `/`, `/admin`, `/specialist` | Interfaz HTML |

La documentación interactiva (`/docs`) solo está disponible en modo desarrollo.

---

## Seguridad (principios)

- Contraseñas de acceso almacenadas con hash (bcrypt).
- Autenticación por JWT.
- Autorización por rol y permisos finos.
- Rate limit de login en producción.
- Variables sensibles solo por entorno (no versionadas).

---

## Licencia / créditos

Desarrollado para **Universidad Tominaga Nakamoto**  
Sistema de Gestión de Información para Admisiones  

> Este README es informativo y no incluye credenciales, secretos ni datos operativos de administración.
