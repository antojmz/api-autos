"""
main.py — Punto de entrada de api-usuarios (autenticación + CRUD de usuarios).

Estructura del servicio:
    app/config.py        -> configuración leída desde .env (BD, admin inicial)
    app/database.py      -> conexión a PostgreSQL y sesión por petición
    app/models.py        -> tabla "usuarios" (SQLModel)
    app/schemas.py       -> DTOs de entrada/salida (nunca exponen password_hash)
    app/seguridad.py     -> hash de contraseñas con Argon2id
    app/servicios.py     -> lógica reutilizable (crear usuario, unicidad)
    app/dependencies.py  -> guards: usuario actual (401) y admin (403)
    app/routers/auth.py      -> /auth/registro, /auth/login
    app/routers/usuarios.py  -> /usuarios (CRUD, /me)
    libs/auth-jwt (monorepo) -> emisión y validación de los JWT

Cómo ejecutarla (con Docker, desde la RAÍZ del monorepo; ver docs/services/api-usuarios.md):
    docker compose build api-usuarios
    docker compose up -d api-usuarios
Documentación interactiva: http://127.0.0.1:8001/docs  (botón "Authorize" para iniciar sesión)
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models import Usuario
from app.routers import auth, usuarios
from app.schemas import UsuarioCreateAdmin
from app.servicios import crear_usuario
from auth_jwt import Rol, get_config_jwt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("api_usuarios")

# Falla AL ARRANCAR (no en la primera petición) si falta JWT_SECRET_KEY o es
# demasiado corta: una mala configuración de seguridad debe detectarse pronto.
get_config_jwt()


# ---------------------------------------------------------------------------
# 1. Arranque: administrador inicial
# ---------------------------------------------------------------------------
def crear_admin_inicial() -> None:
    """
    Problema del "huevo y la gallina": solo un admin puede crear admins, y el
    registro público siempre crea usuarios normales. Por eso, si no existe
    ningún admin, se crea uno con ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD
    del .env. Es idempotente: si ya hay un admin, no hace nada.
    """
    if not (settings.admin_username and settings.admin_email and settings.admin_password):
        logger.info("ADMIN_* no configurado: no se crea administrador inicial")
        return

    with Session(engine) as session:
        if session.exec(select(Usuario.id).where(Usuario.rol == Rol.ADMIN)).first() is not None:
            return
        try:
            # Se valida con el mismo esquema que el resto de altas: la
            # contraseña del admin también debe cumplir la política.
            datos = UsuarioCreateAdmin(
                username=settings.admin_username,
                email=settings.admin_email,
                nombre_completo="Administrador",
                password=settings.admin_password.get_secret_value(),
                rol=Rol.ADMIN,
            )
            crear_usuario(
                session,
                username=datos.username,
                email=datos.email,
                nombre_completo=datos.nombre_completo,
                password=datos.password,
                rol=Rol.ADMIN,
            )
            # Nunca se registra la contraseña en los logs.
            logger.info("Administrador inicial '%s' creado", datos.username)
        except ValidationError as exc:
            campos = ", ".join(str(e["loc"][0]) for e in exc.errors())
            logger.error("ADMIN_* no válido (%s): no se crea administrador inicial", campos)
        except HTTPException:
            logger.error("El username o email de ADMIN_* ya existe: no se crea administrador inicial")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    `lifespan`: código que FastAPI ejecuta al ARRANCAR (antes del `yield`) y al
    DETENERSE (después). Las migraciones ya se aplicaron en el entrypoint, así
    que la tabla "usuarios" existe cuando llega aquí.
    """
    crear_admin_inicial()
    yield


app = FastAPI(
    title="API Usuarios",
    description=(
        "Autenticación (JWT) y gestión de usuarios del monorepo.\n\n"
        "1. Regístrate en `POST /auth/registro` o usa el admin inicial.\n"
        "2. Pulsa **Authorize** e inicia sesión: Swagger guardará el token.\n"
        "3. El mismo token sirve en api-autos (cabecera `Authorization: Bearer <token>`)."
    ),
    # La versión la actualiza release-please en cada release (no editar a mano).
    version="1.1.0",  # x-release-please-version
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# 2. Middleware de seguridad
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    # Authorization: el token JWT. El login usa formulario (form-urlencoded),
    # que los navegadores envían sin necesidad de cabeceras extra.
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def agregar_cabeceras_seguridad(request: Request, call_next):
    """Cabeceras HTTP de seguridad básicas en todas las respuestas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Las respuestas contienen tokens y datos personales: que ningún
    # navegador ni proxy intermedio las guarde en caché.
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# 3. Manejo seguro de errores (mismo criterio que api-autos)
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    422 saneado: solo campo y motivo. Es especialmente importante aquí: el
    detalle por defecto de FastAPI incluye el "input", ¡que podría ser una
    contraseña!
    """
    errores = [
        {"campo": ".".join(str(parte) for parte in error["loc"]), "mensaje": error["msg"]} for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Datos de entrada inválidos", "errores": errores},
    )


@app.exception_handler(IntegrityError)
async def manejar_error_integridad(request: Request, exc: IntegrityError) -> JSONResponse:
    """409: p. ej. dos registros simultáneos con el mismo email (índice único)."""
    logger.warning("Violación de integridad en %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "La operación entra en conflicto con los datos existentes"},
    )


@app.exception_handler(SQLAlchemyError)
async def manejar_error_bd(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Error de base de datos en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Servicio de datos no disponible. Intente más tarde."},
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )


# ---------------------------------------------------------------------------
# 4. Registro de rutas
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(usuarios.router)


@app.get("/", tags=["General"], summary="Bienvenida")
def raiz() -> dict[str, str]:
    return {"mensaje": "API Usuarios", "documentacion": "/docs"}
