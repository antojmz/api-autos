# =============================================================================
# justfile — Tareas del monorepo con `just` (https://just.systems).
#
#   brew install just       # instalar (una vez)
#   just                    # ver todas las tareas
#   just setup              # crear los .env que falten
#   just dev                # levantar TODO en modo desarrollo (recarga en caliente)
#
# Los puertos del host se pueden cambiar con variables de entorno, por ejemplo:
#   AUTOS_PORT=8002 just dev
# =============================================================================

# Las recetas se ejecutan con bash y se detienen al primer error.
set shell := ["bash", "-euo", "pipefail", "-c"]

# Compose de desarrollo = base (docker-compose.yml) + overrides de desarrollo.
dc_dev := "docker compose -f docker-compose.yml -f docker-compose.dev.yml"
# Para operaciones que deben ver TODOS los servicios (también `web`, que en
# desarrollo está en el perfil "produccion").
dc_todo := dc_dev + " --profile produccion"

autos_port := env("AUTOS_PORT", "8000")
usuarios_port := env("USUARIOS_PORT", "8001")
web_port := env("WEB_PORT", "3000")

# Lista las tareas disponibles.
default:
    @just --list --unsorted

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

# Crea los .env que falten a partir de los .env.example (nunca sobrescribe) y genera JWT_SECRET_KEY.
setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f .env ]; then
        cp .env.example .env
        clave=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
        sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${clave}|" .env && rm .env.bak
        echo "✔ .env creado con una JWT_SECRET_KEY aleatoria"
    else
        echo "• .env ya existe (no se modifica)"
    fi
    for svc in api-usuarios api-autos; do
        destino="services/${svc}/.env"
        if [ ! -f "$destino" ]; then
            cp "services/${svc}/.env.example" "$destino"
            echo "✔ ${destino} creado: edita DB_PASS (y en api-usuarios, ADMIN_*)"
        else
            echo "• ${destino} ya existe (no se modifica)"
        fi
    done

# -----------------------------------------------------------------------------
# Desarrollo (recarga en caliente)
# -----------------------------------------------------------------------------

# Levanta APIs + frontend en modo DESARROLLO, mostrando los logs (Ctrl+C para detener).
dev: _quitar-web-produccion
    {{dc_dev}} up --build

# Igual que `dev`, pero en segundo plano.
dev-d: _quitar-web-produccion
    {{dc_dev}} up --build -d
    @echo "web: http://127.0.0.1:{{web_port}}  ·  api-usuarios: http://127.0.0.1:{{usuarios_port}}/docs  ·  api-autos: http://127.0.0.1:{{autos_port}}/docs"

# El `web` de producción usa el mismo puerto que `web-dev`: se elimina antes de levantar desarrollo.
_quitar-web-produccion:
    @{{dc_todo}} rm --stop --force web >/dev/null 2>&1 || true

# Comprobación de tipos del frontend (dentro del contenedor web-dev; requiere `just dev`).
typecheck:
    {{dc_dev}} exec web-dev npm run typecheck

# -----------------------------------------------------------------------------
# Producción local (imágenes compiladas, sin recarga)
# -----------------------------------------------------------------------------

# Construye las imágenes de producción.
build:
    docker compose build

# Levanta todo en modo PRODUCCIÓN (en segundo plano). Elimina web-dev si estaba corriendo.
up:
    docker compose up -d --build --remove-orphans
    @echo "web: http://127.0.0.1:{{web_port}}"

# -----------------------------------------------------------------------------
# Comunes
# -----------------------------------------------------------------------------

# Detiene y elimina los contenedores (de cualquiera de los dos modos). Los datos siguen en PostgreSQL.
down:
    {{dc_todo}} down --remove-orphans

# Estado de los contenedores.
ps:
    {{dc_todo}} ps

# Logs en vivo; sin argumento, de todos los servicios (p. ej. `just logs api-autos`).
logs servicio="":
    {{dc_todo}} logs -f {{servicio}}

# Abre una terminal dentro de un contenedor (p. ej. `just shell api-usuarios`).
shell servicio:
    {{dc_todo}} exec {{servicio}} sh

# Aplica las migraciones pendientes; sin argumento, en las dos APIs.
migrate servicio="":
    #!/usr/bin/env bash
    set -euo pipefail
    for svc in {{ if servicio == "" { "api-usuarios api-autos" } else { servicio } }}; do
        echo "→ ${svc}"
        {{dc_todo}} exec "$svc" alembic upgrade head
    done

# Genera una migración a partir de los cambios en app/models.py (p. ej. `just migration api-autos 0002 "agregar color"`).
migration servicio rev mensaje:
    {{dc_dev}} run --rm --no-deps \
        -v "$(pwd)/services/{{servicio}}/alembic/versions:/app/alembic/versions" \
        {{servicio}} alembic revision --autogenerate --rev-id {{rev}} -m "{{mensaje}}"
    @echo "Revisa el archivo en services/{{servicio}}/alembic/versions/ y aplícalo con: just migrate {{servicio}}"

# Ejecuta la colección de Postman completa (o una carpeta: `just test "2. API Autos"`).
test carpeta="":
    #!/usr/bin/env bash
    set -euo pipefail
    clave=$(grep '^ADMIN_PASSWORD=' services/api-usuarios/.env | cut -d= -f2-)
    args=(--env-var "adminPassword=${clave}"
          --env-var "baseUrlAutos=http://127.0.0.1:{{autos_port}}"
          --env-var "baseUrlUsuarios=http://127.0.0.1:{{usuarios_port}}"
          --env-var "baseUrlWeb=http://127.0.0.1:{{web_port}}")
    if [ -n "{{carpeta}}" ]; then args+=(--folder "{{carpeta}}"); fi
    npx -y newman run API_Monorepo.postman_collection.json "${args[@]}"
