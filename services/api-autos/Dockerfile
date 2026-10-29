# =============================================================================
# Dockerfile — Imagen de la API Concesionario de Autos
#
# Se usa un "multi-stage build" (construcción en dos etapas):
#   1. builder: crea un entorno virtual en /opt/venv e instala las dependencias.
#   2. runtime: imagen final que solo copia ese entorno virtual y el código.
# Ventajas: la imagen final es más pequeña y no contiene cachés de pip ni
# herramientas de compilación (menos superficie de ataque).
#
# El contexto de construcción es la RAÍZ del monorepo (para poder instalar la
# librería compartida libs/auth-jwt); por eso las rutas de COPY empiezan con
# services/api-autos/. Qué archivos entran: ver Dockerfile.dockerignore.
#
# Construir (desde la raíz del monorepo):  docker compose build api-autos
# o, sin Compose:  docker build -f services/api-autos/Dockerfile -t api-autos .
# =============================================================================

# -----------------------------------------------------------------------------
# Etapa 1: builder — entorno virtual con las dependencias
# -----------------------------------------------------------------------------
# "slim" = Debian mínimo con Python. Se fija la versión menor (3.13) para que
# las construcciones sean reproducibles.
FROM python:3.13-slim AS builder

# Entorno virtual DENTRO de la imagen: aísla las dependencias de la app de las
# del Python del sistema, igual que un .venv local.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Se copia SOLO requirements.txt antes que el código: Docker cachea esta capa
# y no reinstala las dependencias cada vez que cambia un archivo .py.
COPY services/api-autos/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Librería compartida del monorepo (validación de tokens JWT).
COPY libs/auth-jwt /tmp/libs/auth-jwt
RUN pip install --no-cache-dir /tmp/libs/auth-jwt

# -----------------------------------------------------------------------------
# Etapa 2: runtime — imagen final
# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# PYTHONDONTWRITEBYTECODE: no genera archivos .pyc.
# PYTHONUNBUFFERED: los logs salen inmediatamente (se ven en `docker logs`).
# PATH: el Python y los comandos (uvicorn, alembic) del entorno virtual tienen
# prioridad, así no hace falta "activar" el venv.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Seguridad: la app NO corre como root. Si alguien explotara una
# vulnerabilidad, tendría los permisos mínimos.
RUN groupadd --system appuser && useradd --system --gid appuser --no-create-home appuser

WORKDIR /app

# Entorno virtual ya construido en la etapa anterior.
COPY --from=builder /opt/venv /opt/venv

# Código de la aplicación y migraciones. El archivo .env NO se copia (está en
# Dockerfile.dockerignore): las credenciales se pasan al contenedor al ejecutarlo.
COPY --chown=appuser:appuser services/api-autos/alembic.ini ./
COPY --chown=appuser:appuser services/api-autos/alembic ./alembic
COPY --chown=appuser:appuser services/api-autos/app ./app
COPY --chown=appuser:appuser --chmod=755 services/api-autos/docker/entrypoint.sh ./docker/entrypoint.sh

USER appuser

# Documenta el puerto en el que escucha uvicorn dentro del contenedor.
EXPOSE 8000

# Docker comprueba periódicamente que la API responde; `docker compose ps`
# mostrará "healthy" o "unhealthy". Se usa Python (ya incluido) en vez de curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"]

# El entrypoint aplica las migraciones y luego arranca uvicorn.
ENTRYPOINT ["/app/docker/entrypoint.sh"]
