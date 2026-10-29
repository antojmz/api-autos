# Arquitectura del monorepo

## Estructura

```
.
├── services/              Backends (APIs, workers). Uno por carpeta.
│   ├── api-usuarios/      Autenticación (JWT) y CRUD de usuarios
│   └── api-autos/         CRUD de autos y modelos (rutas protegidas con JWT)
├── apps/                  Frontends. Uno por carpeta.
│   └── web/               Nuxt 4 + Vuetify 4, con BFF (cookie httpOnly)
├── libs/                  Código compartido entre servicios y/o apps
│   └── auth-jwt/          Emisión y validación de JWT (paquete Python)
├── docs/                  Toda la documentación
├── docker-compose.yml     Orquesta todos los servicios y apps
├── API_Monorepo.postman_collection.json  Pruebas end-to-end de todas las APIs y el BFF
├── .env                   Configuración compartida (JWT_SECRET_KEY). No se versiona.
├── .github/workflows/     release-please (releases) y pr-title (valida Conventional Commits)
├── release-please-config.json, .release-please-manifest.json, version.txt
│                          versión única del monorepo (ver docs/releases.md)
├── README.md              Presentación y arranque rápido
└── CLAUDE.md              Contexto para agentes de IA (hay uno más por servicio)
```

```
  navegador ──► ┌──────────────┐  1. login   ┌───────────────────────┐
  (cookie       │ apps/web     │ ──────────► │ services/api-usuarios │ ── emite JWT
   httpOnly)    │ :3000  BFF   │ ◄── token ─ │ :8001                 │
                └──────┬───────┘             └───────────┬───────────┘
                       │ 2. Authorization: Bearer        │ tabla usuarios
                       │    (lo añade el BFF)            │
                       ▼                                 │
                ┌──────────────────────┐                │
                │ services/api-autos   │                │
                │ :8000  valida el JWT │                │
                └──────────┬───────────┘                │
                           │ tablas autos, modelos      │
                           ▼                            ▼
                ┌─────────────────────────────────────────────────┐
                │ PostgreSQL de la máquina — BD "autos", public   │
                │ (host.docker.internal:5432 desde los contenedores) │
                └─────────────────────────────────────────────────┘

   libs/auth-jwt: instalada en las imágenes de ambos servicios.
   El navegador solo habla con apps/web; el token nunca llega a JavaScript (ver apps/web.md).
```

## Autenticación entre servicios

- `api-usuarios` es el **único** servicio que conoce las contraseñas (las guarda como hash Argon2id) y el único que **emite** tokens.
- Los demás servicios **validan** el token localmente con `libs/auth-jwt`, sin llamar a `api-usuarios`. Comprueban la firma con la clave compartida `JWT_SECRET_KEY` y también `exp`, `iss` y `aud`.
- La clave vive en el `.env` de la raíz y `docker-compose.yml` la inyecta a todos los servicios. Compose no arranca si falta.
- Los roles (`admin`, `usuario`) viajan dentro del token y están definidos una sola vez, en `auth_jwt.Rol`.
- Más detalles y límites de este diseño: [libs/auth-jwt.md](libs/auth-jwt.md).

## Base de datos compartida

Todos los servicios usan **la misma base de datos** (`autos`, esquema `public`), pero cada uno es **dueño** de sus tablas:

| Servicio | Tablas | Tabla de versiones de Alembic |
|---|---|---|
| `api-autos` | `autos`, `modelos` | `alembic_version` |
| `api-usuarios` | `usuarios` | `alembic_version_usuarios` |

Reglas:
- Un servicio solo lee y escribe **sus** tablas. Si necesita datos de otro servicio, los pide por HTTP o los toma del token.
- No hay claves foráneas entre tablas de servicios distintos.
- Cada servicio tiene su propia tabla de versiones de Alembic (`version_table`), y en `alembic/env.py` un `include_object` hace que ignore las tablas de los demás. Sin esto, el autogenerate propondría borrar las tablas ajenas.

## Convenciones

- **Cada servicio, app o librería es autocontenido** en su carpeta: su `Dockerfile`, sus dependencias (`requirements.txt`, `package.json`...), su `.env.example` y su `CLAUDE.md` si hace falta.
- **Nombres de carpeta** en kebab-case, por ejemplo `services/api-autos` o `apps/web-concesionario`. El nombre de la carpeta es también el nombre del servicio en `docker-compose.yml` y el de la imagen.
- **Un solo `docker-compose.yml`, en la raíz.** Todos los comandos `docker compose ...` se ejecutan desde la raíz del repositorio.
- **Contexto de construcción en la raíz.** Los servicios se construyen con `build: {context: ., dockerfile: services/<svc>/Dockerfile}`, para que la imagen pueda incluir `libs/`. Cada Dockerfile tiene al lado su `Dockerfile.dockerignore` con una **lista blanca** (excluye todo y permite solo lo necesario), así nunca entran a la imagen los `.env` ni el código de otros servicios.
- **Credenciales**:
  - Cada servicio tiene su `.env`, y la configuración compartida va en el `.env` de la raíz.
  - Ninguno se versiona (`.gitignore` de la raíz) ni entra en las imágenes.
  - Siempre se mantiene un `.env.example` sin secretos.
- **Documentación**: solo en `docs/`. El código lleva comentarios, pero las guías, procedimientos y decisiones van aquí.
- **Dependencias entre carpetas**:
  - Las apps hablan con los servicios por HTTP; nunca importan su código.
  - Lo que se comparte va a `libs/`.
  - Un servicio no importa código de otro servicio.

## Cómo añadir…

### Un servicio (backend)
1. Crear `services/<nombre>/` con su `Dockerfile`, `Dockerfile.dockerignore` (lista blanca) y `.env.example`. Copiar como base los de `api-autos`.
2. Añadir el bloque `<nombre>:` en `docker-compose.yml` con `<<: *servicio-python` (si es Python), `build: {context: ., dockerfile: services/<nombre>/Dockerfile}`, `env_file` y un puerto de host libre.
3. Si tiene tablas propias, darle su propia `version_table` de Alembic y el `include_object` en `alembic/env.py`.
4. Para proteger sus rutas, instalar `libs/auth-jwt` y usar `obtener_claims` y `requiere_rol`.
5. Documentarlo en `docs/services/<nombre>.md` y enlazarlo en `docs/README.md`.

### Una app (frontend)
1. Crear `apps/<nombre>/` con el framework elegido. Toma `apps/web` como referencia: Dockerfile, `Dockerfile.dockerignore` y BFF.
2. Si va en Docker, añadir su bloque en `docker-compose.yml` (con `depends_on` de las APIs que consuma).
3. Autenticación recomendada: **BFF** como en `apps/web`. El servidor de la app hace el login, guarda el token en una cookie `httpOnly` y hace de proxy hacia las APIs. Así no hay CORS y el token nunca llega al JavaScript del navegador.
   - Si la app llama a las APIs **directamente** desde el navegador, hay que añadir su origen a `CORS_ORIGINS` de cada servicio.
4. Documentarla en `docs/apps/<nombre>.md`.
5. Si llegan a existir varias apps JavaScript, evaluar en ese momento un gestor de workspaces (pnpm workspaces, Turborepo o Nx).

### Una librería compartida
1. Crear `libs/<nombre>/` con su gestor de paquetes (`pyproject.toml` para Python, `package.json` para JS).
2. En los servicios que la usen, añadir al Dockerfile el `COPY libs/<nombre>` y el `pip install`, y permitir la carpeta en su `Dockerfile.dockerignore`.
3. Documentarla en `docs/libs/<nombre>.md`.

## Servicios y librerías actuales

| Carpeta | Tipo | Tecnología | Puerto (host) | Documentación |
|---|---|---|---|---|
| `services/api-usuarios` | Backend | FastAPI, SQLModel, Alembic, PyJWT, Argon2 | 8001 (`USUARIOS_PORT`) | [services/api-usuarios.md](services/api-usuarios.md) |
| `services/api-autos` | Backend | FastAPI, SQLModel, Alembic | 8000 (`AUTOS_PORT`) | [services/api-autos.md](services/api-autos.md) |
| `apps/web` | Frontend | Nuxt 4, Vuetify 4, BFF en Nitro | 3000 (`WEB_PORT`) | [apps/web.md](apps/web.md) |
| `libs/auth-jwt` | Librería Python | PyJWT, FastAPI | — | [libs/auth-jwt.md](libs/auth-jwt.md) |
