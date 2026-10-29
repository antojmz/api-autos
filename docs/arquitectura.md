# Arquitectura del monorepo

## Estructura

```
.
├── services/              Backends (APIs, workers). Uno por carpeta.
│   └── api-autos/         FastAPI + PostgreSQL + Alembic, en Docker
├── apps/                  Frontends. Uno por carpeta. (Vacío por ahora)
├── libs/                  Código compartido entre servicios y/o apps. (Vacío por ahora)
├── docs/                  Toda la documentación
├── docker-compose.yml     Orquesta todos los servicios y apps
├── README.md              Presentación y arranque rápido
└── CLAUDE.md              Contexto para agentes de IA (hay uno más por servicio)
```

```
             ┌─────────────┐        HTTP        ┌──────────────────────┐
  usuario ──►│ apps/<web>  │ ─────────────────► │ services/api-autos   │
             │ (futuro)    │                    │ contenedor Docker    │
             └─────────────┘                    └──────────┬───────────┘
                    ▲                                      │ host.docker.internal:5432
                    │ importan                             ▼
             ┌─────────────┐                    ┌──────────────────────┐
             │ libs/<lib>  │                    │ PostgreSQL (en la    │
             │ (futuro)    │                    │ máquina, BD "autos") │
             └─────────────┘                    └──────────────────────┘
```

## Convenciones

- **Cada servicio, app o librería es autocontenido** en su carpeta: su propio `Dockerfile`, sus dependencias (`requirements.txt`, `package.json`...), su `.env.example` y su `CLAUDE.md` si hace falta.
- **Nombres de carpeta** en kebab-case, por ejemplo `services/api-autos` o `apps/web-concesionario`. El nombre de la carpeta es también el nombre del servicio en `docker-compose.yml` y el de la imagen.
- **Un solo `docker-compose.yml`, en la raíz.** Todos los comandos `docker compose ...` se ejecutan desde la raíz del repositorio.
- **Credenciales**: cada servicio tiene su propio `.env`, que nunca se versiona (`.gitignore` de la raíz). Se mantiene un `.env.example` sin secretos.
- **Documentación**: solo en `docs/`. El código lleva comentarios, pero las guías, procedimientos y decisiones van aquí.
- **Dependencias entre carpetas**:
  - Las apps hablan con los servicios por HTTP; nunca importan su código.
  - Lo que se comparte va a `libs/`.
  - Un servicio no importa código de otro servicio.

## Cómo añadir…

### Un servicio (backend)
1. Crear `services/<nombre>/` con su `Dockerfile`, `.dockerignore` y `.env.example`.
2. Añadir el bloque `<nombre>:` en `docker-compose.yml` con `build: ./services/<nombre>` y `env_file: ./services/<nombre>/.env`. Usar un puerto de host distinto a los ya ocupados.
3. Documentarlo en `docs/services/<nombre>.md` y enlazarlo en `docs/README.md`.

### Una app (frontend)
1. Crear `apps/<nombre>/` con el framework elegido.
2. Si va en Docker, añadir su bloque en `docker-compose.yml` con `build: ./apps/<nombre>`.
3. Añadir su origen (por ejemplo `http://localhost:5173`) a `CORS_ORIGINS` del servicio que consuma. El backend ya permite por defecto los puertos 3000, 5173 y 8000 de localhost.
4. Documentarla en `docs/apps/<nombre>.md`.
5. Si llegan a existir varias apps JavaScript, evaluar en ese momento un gestor de workspaces (pnpm workspaces, Turborepo o Nx).

### Una librería compartida
1. Crear `libs/<nombre>/` con su gestor de paquetes (`pyproject.toml` para Python, `package.json` para JS).
2. Si la usa un servicio en Docker, el contexto de construcción de ese servicio tiene que poder ver la librería: cambiar en `docker-compose.yml` a `build: { context: ., dockerfile: services/<servicio>/Dockerfile }` y ajustar los `COPY` del Dockerfile.
3. Documentarla en `docs/libs/<nombre>.md`.

## Servicios actuales

| Carpeta | Tipo | Tecnología | Puerto (host) | Documentación |
|---|---|---|---|---|
| `services/api-autos` | Backend | FastAPI, SQLModel, Alembic, PostgreSQL | 8000 (`API_PORT`) | [services/api-autos.md](services/api-autos.md) |
