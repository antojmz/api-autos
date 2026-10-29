# CLAUDE.md — Monorepo

Contexto para agentes que programen en este repositorio.

## Qué es

Monorepo del proyecto Concesionario de Autos. Es un proyecto **educativo**: el código y la documentación se escriben en **español**, con muchos comentarios.

## Estructura

```
services/   backends, uno por carpeta    -> services/api-autos (FastAPI + PostgreSQL)
apps/       frontends, uno por carpeta   -> vacío por ahora
libs/       código compartido            -> vacío por ahora
docs/       TODA la documentación        -> índice en docs/README.md
docker-compose.yml   orquesta todos los servicios y apps (único, en la raíz)
```

Cada servicio o app tiene su propio `CLAUDE.md` con sus reglas. **Antes de tocar `services/api-autos/`, lee `services/api-autos/CLAUDE.md`.**

## Reglas del monorepo

- Backends en `services/<nombre>/`, frontends en `apps/<nombre>/` y código compartido en `libs/<nombre>/`. Los nombres van en kebab-case y coinciden con el nombre del servicio en `docker-compose.yml`.
- Cada carpeta es autocontenida: su `Dockerfile`, sus dependencias, su `.env.example` y su `.env`.
- Hay un único `docker-compose.yml`, en la raíz. Todos los comandos `docker compose` se ejecutan desde la raíz.
- La documentación va **solo en `docs/`**:
  - `docs/services/<nombre>.md`, `docs/apps/<nombre>.md` y `docs/libs/<nombre>.md`.
  - Todo documento nuevo se enlaza en `docs/README.md`.
  - Si cambia la estructura, se actualiza `docs/arquitectura.md`.
- Las apps consumen los servicios por HTTP y nunca importan su código. Un servicio no importa código de otro servicio. Lo compartido va a `libs/`.
- Los `.env` nunca se versionan; `.gitignore` de la raíz los cubre en cualquier carpeta.
- No hay entornos virtuales locales: todo se ejecuta en Docker.
- No añadir herramientas de monorepo JS (pnpm workspaces, Turborepo, Nx) hasta que exista al menos una app que las necesite.

## Comandos (desde la raíz)

```bash
docker compose build                 # todas las imágenes
docker compose up -d                 # todo
docker compose up -d --build <svc>   # reconstruir un servicio tras cambiar su código
docker compose logs -f <svc>
docker compose down
```

En esta máquina, el puerto 8000 del host puede estar ocupado por otro proyecto (`cpat-api`). No lo detengas: usa `API_PORT=8001 docker compose up -d`.

## Verificación

- `services/api-autos`: con la API levantada, ejecutar `npx -y newman run services/api-autos/postman/API_Autos.postman_collection.json`. Deben pasar las 26 peticiones; si la API está en otro puerto, añadir `--env-var baseUrl=http://127.0.0.1:8001`.
