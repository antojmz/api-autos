"""
main.py — Punto de entrada de la API "Concesionario de Autos" (demo educativa).

Estructura del proyecto:
    app/config.py        -> configuración leída desde .env (credenciales)
    app/database.py      -> conexión a PostgreSQL y sesión por petición
    app/models.py        -> tablas (SQLModel / SQLAlchemy)
    app/schemas.py       -> validación de entrada/salida (Pydantic)
    app/dependencies.py  -> inyección de dependencias reutilizables
    app/routers/         -> endpoints agrupados por recurso
    alembic/             -> migraciones que crean/modifican las tablas

Este archivo crea la aplicación, configura la seguridad básica (CORS y
cabeceras), define el manejo centralizado de errores y registra los routers.

Cómo ejecutarla (con Docker, desde la RAÍZ del monorepo; ver docs/services/api-autos.md):
    docker compose build api-autos     # construye la imagen (venv en /opt/venv)
    docker compose up -d api-autos     # aplica migraciones y arranca uvicorn
Documentación interactiva: http://127.0.0.1:8000/docs  (o /redoc)
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import settings
from app.routers import autos, modelos
from auth_jwt import get_config_jwt

# Los detalles técnicos de los errores van al log del SERVIDOR, nunca al cliente.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("api_autos")

# Falla AL ARRANCAR (no en la primera petición) si falta JWT_SECRET_KEY o es
# demasiado corta: sin ella no se pueden validar los tokens.
get_config_jwt()

# ---------------------------------------------------------------------------
# 1. Creación de la aplicación
# ---------------------------------------------------------------------------
# `FastAPI(...)` es el objeto principal. Los metadatos aparecen en /docs.
# FastAPI genera automáticamente el esquema OpenAPI a partir de los tipos y
# modelos Pydantic declarados en cada endpoint.
app = FastAPI(
    title="API Concesionario de Autos",
    description=(
        "Demo educativa de FastAPI + PostgreSQL: CRUD de autos y sus modelos.\n\n"
        "**Autenticación**: todas las rutas (salvo `/`) requieren un token JWT. "
        "Obténlo en api-usuarios (`POST /auth/login`) y pégalo en el botón *Authorize*."
    ),
    # La versión la actualiza release-please en cada release (no editar a mano).
    version="1.1.0",  # x-release-please-version
)

# ---------------------------------------------------------------------------
# 2. Middleware de seguridad
# ---------------------------------------------------------------------------
# Un *middleware* envuelve TODAS las peticiones: se ejecuta antes de llegar al
# endpoint y después de generar la respuesta.

# CORS (Cross-Origin Resource Sharing): indica a los NAVEGADORES qué sitios web
# pueden llamar a esta API con JavaScript. Buenas prácticas:
#   - Lista explícita de orígenes, nunca "*" en una API real.
#   - allow_credentials=False: la API no usa cookies; el token JWT viaja en
#     la cabecera Authorization, que el frontend añade explícitamente.
#     (Combinar "*" con credenciales es una mala configuración clásica.)
#   - Solo los métodos y cabeceras que realmente usamos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    # Authorization: necesaria para enviar el token JWT (Bearer).
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def agregar_cabeceras_seguridad(request: Request, call_next):
    """Cabeceras HTTP de seguridad básicas en todas las respuestas."""
    response = await call_next(request)
    # Impide que el navegador "adivine" el tipo de contenido (MIME sniffing).
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Impide que la API se incruste en un <iframe> (clickjacking).
    response.headers["X-Frame-Options"] = "DENY"
    # No envía la URL de origen a otros sitios.
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ---------------------------------------------------------------------------
# 3. Manejo seguro de errores
# ---------------------------------------------------------------------------
# `@app.exception_handler(TipoDeError)` captura ese tipo de excepción en
# cualquier endpoint y define qué respuesta recibe el cliente.
# Principio OWASP: el cliente recibe un mensaje claro y un código HTTP
# correcto, pero NUNCA trazas (stack traces), SQL ni datos de conexión.


@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    422: los datos de entrada no cumplen el esquema.
    La respuesta por defecto de FastAPI incluye el valor enviado ("input");
    aquí devolvemos solo el campo y el motivo, sin reflejar lo que mandó el
    cliente (evita reflejar contenido malicioso).
    """
    errores = [
        {
            "campo": ".".join(str(parte) for parte in error["loc"]),
            "mensaje": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Datos de entrada inválidos", "errores": errores},
    )


@app.exception_handler(IntegrityError)
async def manejar_error_integridad(request: Request, exc: IntegrityError) -> JSONResponse:
    """409: la base de datos rechazó la operación (restricción violada)."""
    logger.warning("Violación de integridad en %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "La operación entra en conflicto con los datos existentes"},
    )


@app.exception_handler(SQLAlchemyError)
async def manejar_error_bd(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """503: error de base de datos (p. ej. PostgreSQL caído). Sin detalles técnicos."""
    logger.exception("Error de base de datos en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Servicio de datos no disponible. Intente más tarde."},
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, exc: Exception) -> JSONResponse:
    """500: cualquier error no previsto. Se registra completo solo en el servidor."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )


# Nota: los `HTTPException` que lanzamos (404, 409...) usan el manejador por
# defecto de FastAPI, que responde {"detail": "<mensaje>"}.

# ---------------------------------------------------------------------------
# 4. Registro de rutas
# ---------------------------------------------------------------------------
app.include_router(autos.router)
app.include_router(modelos.router)


@app.get("/", tags=["General"], summary="Bienvenida")
def raiz() -> dict[str, str]:
    return {"mensaje": "API Concesionario de Autos", "documentacion": "/docs"}
