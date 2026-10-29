# API Concesionario de Autos (`services/api-autos`)

API REST educativa hecha con **FastAPI**. Permite crear, listar, actualizar y eliminar autos y sus modelos, guardados en **PostgreSQL**. La API corre en un contenedor **Docker**; PostgreSQL es el que ya tienes instalado en tu máquina.

```
┌──────────── Tu máquina ─────────────────────────────┐
│                                                     │
│  Navegador / Postman ──► 127.0.0.1:8000             │
│                              │                      │
│                   ┌──────────▼──────────┐           │
│                   │ Contenedor api-autos│           │
│                   │  /opt/venv (Python) │           │
│                   │  uvicorn + FastAPI  │           │
│                   └──────────┬──────────┘           │
│                              │ host.docker.internal │
│                   ┌──────────▼──────────┐           │
│                   │ PostgreSQL local    │           │
│                   │ :5432  BD "autos"   │           │
│                   └─────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

No necesitas Python ni un entorno virtual en tu máquina. El entorno virtual (`/opt/venv`) se crea **dentro de la imagen** cuando la construyes.

El código del servicio está en `services/api-autos/`. **Todos los comandos de esta guía se ejecutan desde la raíz del monorepo**, donde está el `docker-compose.yml`.

---

## 1. Requisitos

| Requisito | Para qué | Cómo comprobarlo |
|---|---|---|
| Docker Desktop (Docker 24+ con Compose v2) | Construir y ejecutar la API | `docker --version` y `docker compose version` |
| PostgreSQL 15+ en tu máquina, puerto 5432 | Guardar los datos | `pg_isready -h localhost -p 5432` |
| Una base de datos vacía llamada `autos` | La API crea las tablas sola | `psql -h localhost -U postgres -l` |

Si la base `autos` no existe, créala:

```bash
psql -h localhost -U postgres -c "CREATE DATABASE autos;"
```

No hace falta crear tablas a mano. Las crea Alembic (las migraciones) cuando arranca el contenedor.

---

## 2. Levantar la aplicación desde cero

### Paso 1. Configurar las credenciales

```bash
cd /ruta/al/monorepo          # la raíz del repositorio
cp services/api-autos/.env.example services/api-autos/.env
```

Edita `services/api-autos/.env` con los datos de tu PostgreSQL:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_DATABASE=autos
DB_PASS=tu_clave
```

Deja `DB_HOST=localhost` tal como está. Dentro del contenedor, `localhost` sería el propio contenedor, así que el `docker-compose.yml` de la raíz lo reemplaza automáticamente por `host.docker.internal`, que es como el contenedor llega a tu máquina.

El archivo `.env` **no se copia a la imagen** (está en `.dockerignore`) ni se sube a git (está en `.gitignore`). Docker lo lee al ejecutar el contenedor.

### Paso 2. Construir la imagen

```bash
docker compose build api-autos
```

Esto lee `services/api-autos/Dockerfile` y hace lo siguiente:
1. Parte de la imagen oficial `python:3.13-slim`.
2. Crea el entorno virtual `/opt/venv` e instala `requirements.txt`.
3. Copia el código (`app/`, `alembic/`, `alembic.ini`) a una imagen final limpia que se ejecuta con un usuario sin privilegios (`appuser`).

Al terminar tendrás la imagen `api-autos:latest`. Puedes comprobarlo con `docker images api-autos`.

Si prefieres no usar Compose, el equivalente es `docker build -t api-autos services/api-autos`.

### Paso 3. Levantar el contenedor

```bash
docker compose up -d api-autos
```

Al arrancar, el contenedor:
1. Ejecuta `alembic upgrade head`, que crea o actualiza las tablas en PostgreSQL.
2. Inicia la API con uvicorn en el puerto 8000.

### Paso 4. Comprobar que funciona

```bash
docker compose ps                  # STATUS debe pasar a "healthy" (~30 s)
docker compose logs -f api-autos   # logs en vivo (Ctrl+C para salir)
curl http://127.0.0.1:8000/
```

Documentación interactiva:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Si el puerto 8000 está ocupado

```bash
API_PORT=8001 docker compose up -d api-autos
```

La API queda entonces en `http://127.0.0.1:8001`. Dentro del contenedor sigue escuchando en el 8000.

### Sin Docker Compose (solo `docker run`)

```bash
docker build -t api-autos services/api-autos
docker run -d --name api-autos \
  --env-file services/api-autos/.env \
  -e DB_HOST=host.docker.internal \
  --add-host host.docker.internal:host-gateway \
  -p 127.0.0.1:8000:8000 \
  api-autos
```

---

## 3. Operación diaria

| Acción | Comando |
|---|---|
| Ver logs | `docker compose logs -f api-autos` |
| Detener y eliminar el contenedor (los datos siguen en PostgreSQL) | `docker compose down` |
| Volver a levantar | `docker compose up -d api-autos` |
| **Aplicar cambios de código o de `requirements.txt`** | `docker compose up -d --build api-autos` |
| Abrir una terminal dentro del contenedor | `docker compose exec api-autos sh` |
| Levantar sin aplicar migraciones | poner `RUN_MIGRATIONS: "false"` en el `docker-compose.yml` de la raíz |

La imagen contiene una **copia** del código. Si cambias un archivo `.py`, no verás el cambio hasta que reconstruyas la imagen con `--build`.

### Migraciones (Alembic)

```bash
docker compose exec api-autos alembic current          # versión aplicada
docker compose exec api-autos alembic history          # historial
docker compose exec api-autos alembic upgrade head     # aplicar pendientes
docker compose exec api-autos alembic downgrade -1     # revertir la última
```

**Crear una migración nueva** después de modificar `app/models.py`:

```bash
# 1. Reconstruir la imagen para que incluya el models.py nuevo
docker compose build api-autos

# 2. Generar la migración. El -v monta services/api-autos/alembic/versions de tu máquina para que
#    el archivo generado quede en el proyecto y no solo dentro del contenedor.
docker compose run --rm -v "$(pwd)/services/api-autos/alembic/versions:/app/alembic/versions" \
  api-autos alembic revision --autogenerate --rev-id 0002 -m "descripcion del cambio"

# 3. Revisar el archivo generado en services/api-autos/alembic/versions/ y aplicarlo
docker compose up -d --build api-autos
```

**Dejar la base vacía** (borra todos los datos y deja los IDs empezando en 1):

```bash
docker compose exec api-autos alembic downgrade base
docker compose exec api-autos alembic upgrade head
```

---

## 4. Probar la API

### Con Postman
1. *Import* → elige `services/api-autos/postman/API_Autos.postman_collection.json`.
2. Si la API no está en el puerto 8000, cambia la variable de colección `baseUrl`.
3. Ejecuta la colección completa con *Run collection*: 26 peticiones con sus tests. La carpeta "5. Limpieza" borra los datos que crea.

### Desde la terminal (newman, requiere Node.js)

```bash
npx -y newman run services/api-autos/postman/API_Autos.postman_collection.json
# Con otro puerto:
npx -y newman run services/api-autos/postman/API_Autos.postman_collection.json --env-var baseUrl=http://127.0.0.1:8001
```

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Bienvenida |
| POST | `/autos` | Crear un auto |
| GET | `/autos?skip=0&limit=10&marca=toy` | Listar autos (paginado y con filtro opcional por marca) |
| GET | `/autos/{id}` | Obtener un auto |
| PUT | `/autos/{id}` | Reemplazar un auto |
| DELETE | `/autos/{id}` | Eliminar un auto y sus modelos |
| POST | `/modelo` | Crear un modelo de un auto |
| GET | `/modelos/autos` | Listar autos con sus modelos |

---

## 5. Solución de problemas

| Síntoma | Causa probable y solución |
|---|---|
| `bind: address already in use` al hacer `up` | El puerto 8000 está ocupado: `API_PORT=8001 docker compose up -d api-autos`, o busca qué lo usa con `lsof -nP -iTCP:8000 -sTCP:LISTEN`. |
| Los logs muestran `connection refused` hacia `host.docker.internal` | PostgreSQL no está corriendo (`pg_isready -h localhost`), o solo escucha en localhost: en `postgresql.conf`, `listen_addresses = '*'` y reinicia PostgreSQL. |
| Los logs muestran `no pg_hba.conf entry for host "x.x.x.x"` | PostgreSQL rechaza la IP del contenedor. Añade en `pg_hba.conf` la línea `host  autos  postgres  192.168.65.0/24  scram-sha-256` (usa la IP que aparece en el error) y recarga con `sudo -u postgres pg_ctl reload -D <data_dir>` o `SELECT pg_reload_conf();`. |
| `password authentication failed` | Revisa `DB_USER` y `DB_PASS` en `services/api-autos/.env` y vuelve a hacer `docker compose up -d api-autos`. |
| `database "autos" does not exist` | Créala: `psql -h localhost -U postgres -c "CREATE DATABASE autos;"`. |
| El contenedor se reinicia una y otra vez | La migración falló. Mira el motivo con `docker compose logs api-autos`. |
| No veo mis cambios de código | Reconstruye la imagen: `docker compose up -d --build api-autos`. |
| Errores de CORS desde un frontend | Añade su origen a `CORS_ORIGINS` en `services/api-autos/.env` (formato JSON, ver `.env.example`) y reinicia. |

---

## Estructura del servicio

Todas las rutas son relativas a la raíz del monorepo.

```
docker-compose.yml                  (raíz) servicio "api-autos" conectado al PostgreSQL del host
services/api-autos/
├── Dockerfile                      imagen multi-stage (venv en /opt/venv, usuario no root)
├── docker/entrypoint.sh            migraciones + arranque de uvicorn
├── .dockerignore                   excluye .env, .venv, etc. de la imagen
├── .env.example                    plantilla de configuración
├── requirements.txt
├── alembic.ini, alembic/           migraciones de la base de datos
├── app/                            código de la API (ver services/api-autos/CLAUDE.md)
└── postman/API_Autos.postman_collection.json
```
