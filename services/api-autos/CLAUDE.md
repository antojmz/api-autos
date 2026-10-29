# CLAUDE.md — services/api-autos

Contexto para agentes que programen en el backend. Las reglas generales del monorepo están en el `CLAUDE.md` de la raíz. Las rutas de este archivo son relativas a `services/api-autos/`, salvo que se indique otra cosa.

## Qué es

API REST **educativa** (demo) en FastAPI para un concesionario: CRUD de **Autos** y sus **Modelos**, persistida en PostgreSQL. **Todas las rutas, salvo `GET /`, exigen un token JWT** emitido por `services/api-usuarios`. Este servicio solo valida el token con `libs/auth-jwt` (sin consultar usuarios) y no tiene tabla de usuarios.

Es material didáctico: el código está **muy comentado en español**, explicando los conceptos de FastAPI (decoradores, Pydantic, `Depends`, etc.) y los motivos de seguridad (OWASP). Todo código nuevo debe mantener esa misma densidad y estilo de comentarios, en español.

## Stack

- Python 3.13 (se usa la sintaxis de genéricos `class Pagina[T]`)
- FastAPI 0.162, Uvicorn
- SQLModel 0.0.48 (sobre SQLAlchemy 2.1) y psycopg 3 (`postgresql+psycopg`)
- Alembic 1.20 para migraciones
- pydantic-settings para leer `.env`
- PostgreSQL 15 local: base `autos` en `localhost:5432`, compartida con `api-usuarios` (este servicio solo gestiona `autos` y `modelos`)
- `auth-jwt` (librería del monorepo, `libs/auth-jwt`) para validar los tokens

## Comandos

Se ejecutan **desde la raíz del monorepo**, donde está `docker-compose.yml`. El servicio de Compose se llama `api-autos`.

La API **se ejecuta solo en Docker**; no se usa un entorno virtual local. El venv está dentro de la imagen, en `/opt/venv`. PostgreSQL **no** está en Docker: es el instalado en la máquina, y el contenedor llega a él por `host.docker.internal`. La guía completa para usuarios está en `docs/services/api-autos.md`.

```bash
docker compose build api-autos                # construir la imagen api-autos:latest
docker compose up -d api-autos                # arranca: alembic upgrade head + uvicorn
docker compose up -d --build api-autos        # OBLIGATORIO tras cambiar código o requirements.txt
docker compose logs -f api-autos
docker compose down
AUTOS_PORT=8002 docker compose up -d api-autos  # si el 8000 del host está ocupado
# Docs: http://127.0.0.1:8000/docs  |  /redoc

# Migraciones (dentro del contenedor)
docker compose exec api-autos alembic current|upgrade head|downgrade -1
# Nueva migración tras cambiar app/models.py (rebuild primero; el -v deja el archivo en el repo)
docker compose build api-autos
docker compose run --rm -v "$(pwd)/services/api-autos/alembic/versions:/app/alembic/versions" \
  api-autos alembic revision --autogenerate --rev-id 0002 -m "descripcion"

# Pruebas end-to-end (con api-usuarios y api-autos levantados)
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --folder "2. API Autos" --env-var "adminPassword=$PW" [--env-var baseUrlAutos=http://127.0.0.1:8002]

# Vaciar autos y modelos, con los IDs desde 1 (no toca la tabla usuarios)
docker compose exec api-autos alembic downgrade base && docker compose exec api-autos alembic upgrade head
```

No hay tests automatizados en Python. La suite de verificación es la carpeta "2. API Autos" (46 peticiones con asserts) de la colección única `API_Monorepo.postman_collection.json`, en la raíz del monorepo. Debe pasar completa después de cualquier cambio. Obtiene los tokens en `api-usuarios` (carpeta "0. Autenticación") y necesita la variable `adminPassword`.

**Desarrollo con recarga en caliente**: `just dev` (desde la raíz) monta `services/api-autos/app`, `alembic/` y `libs/auth-jwt/src` en el contenedor y arranca uvicorn con `--reload`. Los cambios en Python se aplican solos, sin reconstruir. Las migraciones nuevas se aplican con `just migrate api-autos`, y una dependencia nueva en `requirements.txt` exige reiniciar `just dev`. El modo se activa con `UVICORN_RELOAD=true` en `docker/entrypoint.sh`; en producción no se define.

## Arquitectura

```
app/
├── config.py        Settings (pydantic-settings) desde .env; database_url con URL.create; cors_origins
├── database.py      engine (pool_pre_ping) + get_session() con yield
├── models.py        TABLAS SQLModel (table=True): Auto, Modelo
├── schemas.py       Esquemas Pydantic de entrada/salida + validadores reutilizables
├── dependencies.py  SessionDep, PaginacionDep, AutoDep (obtener_auto_o_404), ModeloDep (obtener_modelo_o_404)
├── routers/
│   ├── autos.py     /autos CRUD (+ _escapar_like); router con Depends(obtener_claims); DELETE con requiere_rol(Rol.ADMIN)
│   └── modelos.py   POST /modelo, GET /modelos, GET /modelos/autos (ANTES de /modelos/{id}), GET/PUT/DELETE /modelos/{id}; DELETE con requiere_rol(Rol.ADMIN)
└── main.py          FastAPI app, get_config_jwt() al importar, CORS, cabeceras, exception handlers, include_router
alembic/             env.py: settings.database_url, SQLModel.metadata, include_object (ignora tablas de otros servicios), version_table por defecto
Dockerfile           multi-stage python:3.13-slim; contexto = raíz; venv /opt/venv con requirements + libs/auth-jwt; usuario appuser; HEALTHCHECK a "/"
docker/entrypoint.sh si recibe argumentos los ejecuta; si no: migraciones (RUN_MIGRATIONS) + uvicorn 0.0.0.0:8000
../../docker-compose.yml  (raíz) servicio api-autos; hereda x-servicio-python (DB_HOST, JWT_SECRET_KEY); puerto 127.0.0.1:${AUTOS_PORT:-8000}
Dockerfile.dockerignore   LISTA BLANCA de lo que entra a la imagen (contexto = raíz)
```

## Endpoints

| Método | Ruta | Acceso | Éxito | Errores |
|---|---|---|---|---|
| GET | `/` | público (HEALTHCHECK) | 200 | |
| POST | `/autos` | token | 201 | 401, 422 |
| GET | `/autos?skip&limit&marca` | token | 200 | 401, 422 (`limit` > 100) |
| GET | `/autos/{auto_id}` | token | 200 | 401, 404, 422 |
| PUT | `/autos/{auto_id}` | token | 200 | 401, 404, 409, 422 |
| DELETE | `/autos/{auto_id}` | token + admin | 204 | 401, 403, 404 |
| POST | `/modelo` | token | 201 | 401, 404 (auto no existe), 422 |
| GET | `/modelos?skip&limit&auto_id` | token | 200 | 401, 422 |
| GET | `/modelos/autos?skip&limit` | token | 200 | 401, 422 |
| GET | `/modelos/{modelo_id}` | token | 200 | 401, 404, 422 |
| PUT | `/modelos/{modelo_id}` | token | 200 | 401, 404, 422 (sin `auto_id`; fecha ≥ la del auto) |
| DELETE | `/modelos/{modelo_id}` | token + admin | 204 | 401, 403, 404 |

Las listas devuelven `Pagina[T]`: `{total, skip, limit, items}`.

## Reglas obligatorias

**Base de datos**
- El esquema se cambia **solo con migraciones de Alembic**. Nunca usar `SQLModel.metadata.create_all()`.
- Después de modificar `app/models.py`: generar la migración con autogenerate, **revisarla a mano** (checks, FKs, índices, `downgrade`), aplicarla y probar `downgrade` y `upgrade`.
- `alembic/script.py.mako` ya importa `sqlmodel`, que hace falta para los tipos `AutoString`.
- Las restricciones importantes se duplican en la BD como defensa en profundidad. Ejemplos: `CheckConstraint` con nombre `ck_<tabla>_<regla>` y FKs con `ondelete="CASCADE"`.
- Los precios se guardan como `Decimal` / `NUMERIC(12,2)`, nunca como `float`.

**Modelos y esquemas**
- Las tablas viven en `models.py` y la validación del cliente en `schemas.py`; no mezclarlas.
- Los esquemas de entrada heredan de `EntradaEstricta` (`extra="forbid"` para evitar mass assignment, y `str_strip_whitespace`).
- Los esquemas de salida heredan de `SalidaORM` (`from_attributes=True`). Los endpoints declaran siempre `response_model`.
- Los objetos ORM se construyen **campo a campo** desde el esquema validado, nunca con `Model(**datos_cliente)` sin filtrar.
- Reutilizar lo que ya existe: `PATRON_TEXTO_SEGURO` (lista blanca de caracteres para textos), `Marca`, `FechaIngreso` (no futura), `_anio_razonable`, `NombreModelo`, `AnioModelo`, `PrecioModelo`, `Pagina[T]`, `SessionDep`, `PaginacionDep`, `AutoDep`, `ModeloDep`. El frontend (`apps/web/app/utils/reglas.ts`) replica estas reglas: si cambias una, actualízala allí también.
- Los patrones de Pydantic usan el motor regex de Rust, que no admite lookarounds.

**Seguridad (OWASP)**
- Todas las consultas pasan por el ORM, que las parametriza. No concatenar SQL. En `LIKE`/`ILIKE`, escapar el texto con `_escapar_like` y `escape="\\"`.
- La paginación tiene `limit` entre 1 y `LIMITE_MAXIMO_PAGINA` (100).
- Errores de negocio: `HTTPException` con 404, 409 o 422 y un `detail` claro en español.
- Para 422 usar `status.HTTP_422_UNPROCESSABLE_CONTENT`; el nombre antiguo está deprecado.
- Respuestas de error:
  - Validación (422): formato saneado `{"detail": ..., "errores": [{"campo", "mensaje"}]}`, sin repetir el `input` del cliente.
  - Errores de base de datos e inesperados: manejadores genéricos de `main.py` (`IntegrityError`→409, `SQLAlchemyError`→503, `Exception`→500).
  - Nunca enviar al cliente trazas, SQL ni datos de conexión; solo se registran con `logger`.
- CORS solo con orígenes explícitos (`settings.cors_origins`), `allow_credentials=False` y métodos limitados. Si se añade un método HTTP, añadirlo también en `allow_methods`.
- Las credenciales van solo en `.env`, que está en `.gitignore`. Mantener `.env.example` actualizado y sin secretos. No escribir la URL de la BD en `alembic.ini`.

**Autenticación**
- Todo router nuevo se declara con `dependencies=[Depends(obtener_claims)]`. Las operaciones de admin añaden `Depends(requiere_rol(Rol.ADMIN))`. Si un endpoint necesita saber quién llama, recibe `claims: ClaimsDep` (`claims.usuario_id`, `claims.rol`).
- `GET /` debe seguir siendo público: lo usa el `HEALTHCHECK`.
- No validar tokens a mano ni duplicar la configuración JWT: usar siempre `auth_jwt`.
- Este servicio no consulta la tabla `usuarios`. Un usuario desactivado conserva acceso hasta que expira su token; es una limitación documentada.

**Base de datos compartida**
- La BD `autos` también contiene la tabla `usuarios`, que pertenece a `api-usuarios`. Nunca la leas ni la migres desde aquí.
- `alembic/env.py` tiene `include_object` para ignorarla; no lo quites.

**Docker**
- `.env` nunca entra a la imagen: se pasa en tiempo de ejecución con `env_file`.
- El contenedor corre como el usuario no root `appuser`.
- Si se añade un archivo o carpeta que la app necesita en tiempo de ejecución, añadir su `COPY services/api-autos/...` en el `Dockerfile` y permitirlo en `Dockerfile.dockerignore`.
- Las dependencias nuevas van en `requirements.txt` y después se reconstruye la imagen.
- La configuración nueva se añade a `Settings` en `app/config.py` y a `.env.example`. Si el valor tiene que ser distinto dentro del contenedor, se pone también en `environment` del servicio `api-autos` en el `docker-compose.yml` de la raíz.

**Mantenimiento**
- Al cambiar cómo se construye o se levanta la aplicación, actualizar `docs/services/api-autos.md` (en la raíz del monorepo).
- Al añadir o cambiar un endpoint, actualizar la carpeta "2. API Autos" de `API_Monorepo.postman_collection.json` (raíz) con casos de éxito y de error y sus `pm.test`, y actualizar la tabla de este archivo.

## Reglas de negocio

- `fecha_ingreso` (de autos y modelos) no puede ser futura. En POST, si no se envía, vale la fecha de hoy. En PUT de auto es obligatoria, porque PUT es un reemplazo completo.
- La `fecha_ingreso` de un modelo debe ser igual o posterior a la de su auto; si no, responde **422**.
- El PUT de un auto no puede poner una fecha posterior a la del modelo más antiguo; si lo hace, responde **409**.
- `marca`: 2 a 50 caracteres. `nombre`: 1 a 60. Ambos con `PATRON_TEXTO_SEGURO`.
- `anio`: desde 1886 hasta el año actual + 1.
- `precio`: mayor que 0, como máximo 99 999 999.99 y con 2 decimales. En el JSON de respuesta sale como string (`"25990.50"`).
- Al borrar un auto se borran sus modelos: `cascade_delete` en el ORM y `ON DELETE CASCADE` en la BD.
- `GET /modelos/autos` usa `selectinload` para evitar el problema N+1, y los modelos se ordenan por id.

## Notas

- La colección de Postman crea datos y los borra en la carpeta "5. Limpieza". Ejecutarla completa o limpiar después.
- Con curl en zsh, no guardar `-H "..."` en una variable: zsh no la separa en palabras y la petición falla con 400.
- El manejador de `Exception` responde 500, pero Starlette vuelve a lanzar la excepción, así que verás la traza en el log de uvicorn. Es el comportamiento esperado.
