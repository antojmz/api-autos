# CLAUDE.md — Monorepo

Contexto para agentes que programen en este repositorio.

## Qué es

Monorepo del proyecto Concesionario de Autos. Es un proyecto **educativo**: el código y la documentación se escriben en **español**, con muchos comentarios.

## Estructura

```
services/api-usuarios/  autenticación (registro, login JWT) y CRUD de usuarios; único que emite tokens
services/api-autos/     CRUD de autos y modelos; todas sus rutas (salvo "/") exigen token
libs/auth-jwt/          paquete Python auth_jwt: emitir/validar JWT, Rol, guards de FastAPI
apps/                   frontends, uno por carpeta -> vacío por ahora
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
- No hay entornos virtuales locales: todo se ejecuta en Docker.
- No añadir herramientas de monorepo JS (pnpm workspaces, Turborepo, Nx) hasta que exista al menos una app que las necesite.

## Commits y releases

- **Conventional Commits obligatorio**: `tipo(scope opcional): descripción en español`.
  - Tipos: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore` y `revert`.
  - Scopes: `api-autos`, `api-usuarios`, `auth-jwt`, `docs` y `monorepo`.
  - Para un cambio incompatible: `feat!:` o el pie `BREAKING CHANGE:`.
- release-please calcula la versión a partir de esos mensajes. Usa una **sola versión para todo el repo**, con tags `vX.Y.Z`.
- **No editar a mano** `version.txt`, `.release-please-manifest.json`, `CHANGELOG.md` ni las líneas marcadas `# x-release-please-version` (`version=` en los `main.py`, y `version` en `libs/auth-jwt/pyproject.toml`).
- Si se añade un archivo nuevo con versión, registrarlo en `extra-files` de `release-please-config.json`.
- Guía completa: `docs/releases.md`.

## Comandos (desde la raíz)

```bash
docker compose build                 # todas las imágenes
docker compose up -d                 # todo (api-usuarios :8001, api-autos :8000)
docker compose up -d --build <svc>   # reconstruir un servicio tras cambiar su código
docker compose logs -f <svc>
docker compose exec <svc> alembic check   # no debe proponer cambios
docker compose down
```

En esta máquina, el puerto 8000 del host puede estar ocupado por otro proyecto (`cpat-api`). No lo detengas: usa `AUTOS_PORT=8002 docker compose up -d`.

## Verificación

Con los servicios levantados, deben pasar completas las dos colecciones de Postman. La contraseña del admin es `ADMIN_PASSWORD` de `services/api-usuarios/.env`.

```bash
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run services/api-usuarios/postman/API_Usuarios.postman_collection.json --env-var "adminPassword=$PW"
npx -y newman run services/api-autos/postman/API_Autos.postman_collection.json --env-var "adminPassword=$PW" \
  [--env-var baseUrl=http://127.0.0.1:8002]
```

`api-usuarios` tiene 41 peticiones y `api-autos` 35.
