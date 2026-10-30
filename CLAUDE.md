# CLAUDE.md — Monorepo

Contexto para agentes que programen en este repositorio.

## Qué es

Monorepo del proyecto Concesionario de Autos. Es un proyecto **educativo**: el código y la documentación se escriben en **español**, con muchos comentarios.

## Estructura

```
services/api-usuarios/  autenticación (registro, login JWT) y CRUD de usuarios; único que emite tokens
services/api-autos/     CRUD de autos y modelos; todas sus rutas (salvo "/") exigen token
libs/auth-jwt/          paquete Python auth_jwt: emitir/validar JWT, Rol, guards de FastAPI
apps/web/               frontend Nuxt 4 + Vuetify 4; BFF (server/) con el JWT en cookie httpOnly; único punto que habla con el navegador
docs/                   TODA la documentación -> índice en docs/README.md
docker-compose.yml      orquesta todos los servicios (único, en la raíz)
.env                    (raíz, no versionado) JWT_SECRET_KEY compartida
```

Cada servicio tiene su propio `CLAUDE.md` con sus reglas. **Antes de tocar un servicio, lee su `services/<svc>/CLAUDE.md`.**

## Reglas del monorepo

**Estructura**
- Backends en `services/<nombre>/`, frontends en `apps/<nombre>/` y código compartido en `libs/<nombre>/`. Los nombres van en kebab-case y coinciden con el nombre del servicio en `docker-compose.yml`.
- Cada carpeta es autocontenida: su `Dockerfile`, su `Dockerfile.dockerignore`, sus dependencias, su `.env.example` y su `.env`.
- Hay un único `docker-compose.yml`, en la raíz. Todos los comandos `docker compose` se ejecutan desde la raíz.
- **El contexto de build es la raíz** (`build: {context: ., dockerfile: services/<svc>/Dockerfile}`):
  - Los `COPY` usan rutas `services/<svc>/...` y `libs/...`.
  - Lo que entra a la imagen lo decide la lista blanca de `services/<svc>/Dockerfile.dockerignore`.
  - Si una imagen necesita un archivo nuevo, hay que permitirlo ahí.
- Los servicios Python heredan `x-servicio-python` en el compose (`DB_HOST`, `JWT_*`, `extra_hosts`, `restart`).

**Base de datos compartida**
- Una sola BD, `autos`, en el esquema `public`. Cada servicio es dueño de sus tablas: `api-autos` de `autos` y `modelos`; `api-usuarios` de `usuarios`.
- Un servicio nunca lee ni escribe tablas de otro, y no hay claves foráneas entre servicios.
- Cada servicio tiene su `version_table` de Alembic (`alembic_version` y `alembic_version_usuarios`) y un `include_object` en `alembic/env.py` que ignora las tablas ajenas. Hay que conservarlo en servicios nuevos.

**Autenticación**
- Solo `api-usuarios` emite tokens. Los demás servicios los validan con `auth_jwt.obtener_claims` y `requiere_rol`, sin llamar a `api-usuarios`.
- `JWT_SECRET_KEY` vive **solo** en el `.env` de la raíz y Compose la inyecta. No ponerla en los `.env` de los servicios.
- La configuración JWT y el enum `Rol` están en `libs/auth-jwt`; no se duplican en los servicios.
- Si cambias `libs/auth-jwt`, reconstruye **todos** los servicios: `docker compose up -d --build`.

**Documentación**
- Va **solo en `docs/`**: `docs/services/<nombre>.md`, `docs/apps/<nombre>.md` y `docs/libs/<nombre>.md`.
- Todo documento nuevo se enlaza en `docs/README.md`.
- Si cambia la estructura, la autenticación o la BD compartida, se actualiza `docs/arquitectura.md`.

**Otras**
- Las apps consumen los servicios por HTTP y nunca importan su código. Un servicio no importa código de otro servicio. Lo compartido va a `libs/`.
- Los `.env` nunca se versionan; `.gitignore` de la raíz los cubre en cualquier carpeta.
- No hay entornos virtuales locales de Python: todo se ejecuta en Docker. Para desarrollar, `just dev` (recarga en caliente de las APIs y del front, sin Node ni Python locales). `npm run dev` local en `apps/web` también funciona, pero requiere Node 24.15 o superior.
- No añadir herramientas de monorepo JS (pnpm workspaces, Turborepo, Nx) hasta que exista al menos una app que las necesite.

## Commits y releases

- **Conventional Commits obligatorio**: `tipo(scope opcional): descripción en español`.
  - Tipos: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore` y `revert`.
  - Scopes: `api-autos`, `api-usuarios`, `auth-jwt`, `web`, `docs` y `monorepo`.
  - Para un cambio incompatible: `feat!:` o el pie `BREAKING CHANGE:`.
- **Nombres de rama**: `tipo/scope/descripcion` (el scope es opcional), por ejemplo `feat/api-autos/filtro-por-fechas`. El workflow `.github/workflows/pr-title.yml` genera con ella el título del PR (`feat(api-autos): filtro por fechas`) cuando el título no es convencional, y lo valida.
  - Los tipos y scopes permitidos están definidos en **dos sitios**, que hay que mantener iguales: `.github/workflows/pr-title.yml` (títulos de PR; también los alias de ramas) y `.pre-commit-config.yaml` (hook `commit-msg`). Al añadir un servicio, app o librería, agrega su scope en los dos.
- **pre-commit** (`.pre-commit-config.yaml`, se instala con `just hooks`) se ejecuta en cada commit:
  - higiene de archivos;
  - gitleaks (secretos);
  - Ruff (`ruff.toml`: lint + formato de `services/` y `libs/`, línea de 120 caracteres; `SIM103` desactivada a propósito, por legibilidad);
  - Conventional Commits en el mensaje.
  - El código Python debe pasar `just lint` (o `pre-commit run --all-files`) sin cambios. No usar `--no-verify`.
- release-please calcula la versión a partir de esos mensajes. Usa una **sola versión para todo el repo**, con tags `vX.Y.Z`.
- **No editar a mano** `version.txt`, `.release-please-manifest.json`, `CHANGELOG.md` ni las líneas marcadas `# x-release-please-version` (`version=` en los `main.py`, y `version` en `libs/auth-jwt/pyproject.toml`).
- Si se añade un archivo nuevo con versión, registrarlo en `extra-files` de `release-please-config.json`.
- Guía completa: `docs/releases.md`.

## Comandos (desde la raíz)

**Para desarrollar, usa `just`** (`justfile` en la raíz; `just` lista las tareas):

```bash
just setup                           # crea los .env que falten
just dev                             # TODO en modo desarrollo: código montado + recarga en caliente
just dev-d / just down / just ps / just logs <svc>
just migrate [svc]                   # aplicar migraciones (no requiere reiniciar)
just migration <svc> <rev> "<msg>"   # autogenerar migración (usa el código montado)
just test ["carpeta"]                # colección de Postman
just typecheck                       # tipos del frontend (dentro de web-dev)
just up                              # modo producción
```

Modo desarrollo = `docker-compose.yml` + `docker-compose.dev.yml`:
- **APIs**: montan `app/`, `alembic/` y `libs/auth-jwt/src` en solo lectura, con uvicorn `--reload` (`UVICORN_RELOAD=true` en el entrypoint) y `WATCHFILES_FORCE_POLLING`.
- **Frontend**: corre en `web-dev` (`node:24-slim`, `nuxt dev`, `node_modules` en un volumen propio) en lugar de `web`, que pasa al perfil `produccion`.
- **Cuándo reiniciar `just dev`**: si cambias dependencias, un Dockerfile, un entrypoint o los archivos de Compose.

Docker Compose directo (producción):

```bash
docker compose build                 # todas las imágenes
docker compose up -d                 # todo (web :3000, api-usuarios :8001, api-autos :8000)
docker compose up -d --build <svc>   # reconstruir un servicio tras cambiar su código
docker compose logs -f <svc>
docker compose exec <svc> alembic check   # no debe proponer cambios
docker compose down
```

En esta máquina, el puerto 8000 del host puede estar ocupado por otro proyecto (`cpat-api`). No lo detengas: usa `AUTOS_PORT=8002 just dev` (o `AUTOS_PORT=8002 docker compose up -d`).

## Verificación

La suite end-to-end es **una sola colección de Postman en la raíz**: `API_Monorepo.postman_collection.json`. Tiene tres carpetas:

| Carpeta | Peticiones |
|---|---|
| `1. API Usuarios` | 41 |
| `2. API Autos` | 46 |
| `3. Web (BFF)` | 17 |

En total son 104 peticiones y deben pasar todas. Cada carpeta obtiene sus propios tokens, así que también se puede ejecutar sola con `--folder`.

Un test de colección comprueba en **todas** las respuestas que no aparezcan `password_hash` ni `$argon2`.

```bash
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --env-var "adminPassword=$PW" \
  [--env-var baseUrlAutos=http://127.0.0.1:8002] [--folder "2. API Autos"]
```

Al añadir o cambiar un endpoint (en cualquier servicio o en el BFF), actualiza la carpeta correspondiente de esta colección con casos de éxito y de error.

Frontend: `cd apps/web && npm run typecheck && npm run build` debe pasar sin errores (ver `apps/web/CLAUDE.md`).
