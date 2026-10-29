#!/bin/sh
# =============================================================================
# entrypoint.sh — Se ejecuta cada vez que arranca el contenedor.
#
# 1. Aplica las migraciones pendientes (alembic upgrade head), salvo que
#    RUN_MIGRATIONS=false.
# 2. Arranca la API con uvicorn.
#
# Si se pasa un comando al contenedor, se ejecuta ese comando en su lugar.
# Ejemplo: docker compose run --rm api-autos alembic current
# =============================================================================

# set -e: si un comando falla (p. ej. la migración), el contenedor se detiene
# en vez de arrancar la API con un esquema de BD incorrecto.
set -e

if [ "$#" -gt 0 ]; then
    # `exec` reemplaza este script por el comando: recibe directamente las
    # señales de Docker (Ctrl+C, docker stop).
    exec "$@"
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Aplicando migraciones de base de datos..."
    alembic upgrade head
fi

# Modo desarrollo (docker-compose.dev.yml, `just dev`): UVICORN_RELOAD=true
# reinicia la API automáticamente al guardar un archivo. El código llega por
# bind mount desde tu máquina, así que no hace falta reconstruir la imagen.
# En producción esta variable no se define y uvicorn arranca sin --reload.
if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
    set -- --reload --reload-dir /app/app
    # La librería compartida, si está montada, también se vigila.
    if [ -d /libs/auth-jwt/src ]; then
        set -- "$@" --reload-dir /libs/auth-jwt/src
    fi
    echo "Modo desarrollo: recarga automática activada"
fi

echo "Iniciando la API en el puerto 8000..."
# --host 0.0.0.0: dentro de un contenedor hay que escuchar en todas las
# interfaces; con 127.0.0.1 la API no sería accesible desde fuera.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
