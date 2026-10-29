# CLAUDE.md — services/api-usuarios

Contexto para agentes que programen en este servicio. Las reglas generales del monorepo están en el `CLAUDE.md` de la raíz. Las rutas son relativas a `services/api-usuarios/`, salvo que se indique otra cosa.

## Qué es

Servicio de **autenticación** (registro, login con JWT) y **CRUD de usuarios** con roles (`admin`, `usuario`) y soft delete. Es el **único** servicio que conoce las contraseñas y el único que **emite** tokens; los demás servicios los validan con `libs/auth-jwt`.

Igual que el resto del monorepo, es material didáctico: el código va **muy comentado en español**, explicando el porqué de cada medida de seguridad.

## Stack

- Python 3.13, FastAPI 0.162, SQLModel + psycopg 3, Alembic, pydantic-settings
- `auth-jwt` (`libs/auth-jwt`): PyJWT HS256, `Rol`, `crear_token_acceso` y `decodificar_token`
- `pwdlib[argon2]` (Argon2id), `email-validator` (`EmailStr`) y `python-multipart` (formulario OAuth2 del login)
- PostgreSQL local: la **misma BD `autos`** que `api-autos`. Este servicio solo gestiona la tabla `usuarios`.

## Comandos (desde la raíz del monorepo)

```bash
docker compose build api-usuarios
docker compose up -d api-usuarios            # migraciones + admin inicial + uvicorn (host :8001)
docker compose up -d --build api-usuarios    # tras cambiar código, requirements o libs/auth-jwt
docker compose logs -f api-usuarios
docker compose exec api-usuarios alembic current|check|upgrade head|downgrade -1
# Nueva migración (rebuild primero; el -v deja el archivo en el repo)
docker compose run --rm -v "$(pwd)/services/api-usuarios/alembic/versions:/app/alembic/versions" \
  api-usuarios alembic revision --autogenerate --rev-id 0002 -m "descripcion"
# Pruebas end-to-end
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --folder "1. API Usuarios" --env-var "adminPassword=$PW"
```

La carpeta "1. API Usuarios" (41 peticiones) de la colección única `API_Monorepo.postman_collection.json` (raíz) es la suite de verificación y debe pasar completa. Un test de colección comprueba, en **todas** las respuestas, que no aparezcan `password_hash` ni `$argon2`. Cada ejecución usa un `runId` único, porque los usuarios eliminados dejan reservados su username y su email.

## Arquitectura

```
app/
├── config.py        Settings: DB_*, ADMIN_* (password como SecretStr), cors_origins. JWT NO va aquí (auth_jwt.ConfigJWT)
├── database.py      engine + get_session()
├── models.py        tabla Usuario: username/email únicos en minúsculas (CHECK), password_hash, rol (CHECK), activo, creado_en/actualizado_en/eliminado_en (timestamptz)
├── schemas.py       EntradaEstricta, EntradaParcial (PATCH: prohíbe null), Username, Email, NombreCompleto, Password; UsuarioPublic (sin password_hash), Token, Pagina[T]
├── seguridad.py     hashear_password, verificar_password, simular_verificacion (hash ficticio para igualar tiempos)
├── servicios.py     verificar_unicidad (409), crear_usuario (hashea antes de guardar), marcar_actualizado
├── dependencies.py  SessionDep, PaginacionDep, obtener_usuario_actual (OAuth2PasswordBearer + BD, 401), requiere_admin (rol de la BD, 403), obtener_usuario_o_404
├── routers/auth.py      POST /auth/registro (rol siempre usuario), POST /auth/login (formulario OAuth2; username o email)
├── routers/usuarios.py  /usuarios/me (GET, PATCH, PUT password) ANTES que /usuarios/{id}; CRUD de admin; soft delete
└── main.py          get_config_jwt() al importar; lifespan -> crear_admin_inicial(); CORS (+PATCH, Authorization); cabeceras (+Cache-Control: no-store); manejadores de errores
alembic/             env.py: version_table="alembic_version_usuarios" + include_object (ignora autos/modelos)
Dockerfile, Dockerfile.dockerignore (lista blanca, contexto = raíz), docker/entrypoint.sh
```

## Endpoints

| Método | Ruta | Acceso | Éxito | Errores |
|---|---|---|---|---|
| GET | `/` | público (HEALTHCHECK) | 200 | |
| POST | `/auth/registro` | público | 201 | 409, 422 |
| POST | `/auth/login` | público (form) | 200 | 401, 422 |
| GET | `/usuarios/me` | autenticado | 200 | 401 |
| PATCH | `/usuarios/me` | autenticado | 200 | 401, 409, 422 |
| PUT | `/usuarios/me/password` | autenticado | 204 | 400, 401, 422 |
| POST | `/usuarios` | admin | 201 | 401, 403, 409, 422 |
| GET | `/usuarios?skip&limit&q&rol&activo` | admin | 200 | 401, 403, 422 |
| GET | `/usuarios/{id}` | admin o el propio usuario | 200 | 401, 403, 404 |
| PATCH | `/usuarios/{id}` | admin | 200 | 400, 401, 403, 404, 409, 422 |
| DELETE | `/usuarios/{id}` | admin | 204 | 400, 401, 403, 404 |

## Reglas obligatorias

**Contraseñas**
- Nunca se guardan ni se registran en texto plano. Toda escritura de contraseña pasa por `hashear_password`, también cuando la cambia un admin.
- Nunca se devuelve `password_hash`. Toda respuesta usa `UsuarioPublic` (o `Token`) como `response_model`.
- Las contraseñas **no se recortan** (`StringConstraints(strip_whitespace=False)`). Su política vive en `Password`: de 10 a 128 caracteres, con al menos una letra y un número.
- Los errores 422 no reflejan el `input`, porque podría ser una contraseña. No cambiar el manejador.

**Login**
- Un solo mensaje, `Credenciales incorrectas` (401), para usuario inexistente, contraseña mala o cuenta inactiva.
- Si el usuario no existe, se llama a `simular_verificacion` para igualar los tiempos.

**Autorización**
- `obtener_usuario_actual` valida el token **y** carga el usuario de la BD (401 si no existe o está inactivo).
- `requiere_admin` usa el **rol de la BD**, no el del token.
- Comprobar siempre la propiedad del objeto (admin o el propio usuario) en las rutas por ID (OWASP BOLA).

**Mass assignment**
- `RegistroUsuario` y `UsuarioUpdateMe` no tienen `rol` ni `activo`, y `extra="forbid"` los rechaza.
- Solo los esquemas de admin (`UsuarioCreateAdmin`, `UsuarioUpdateAdmin`) pueden fijarlos.

**Integridad**
- `username` y `email` se normalizan a minúsculas en el esquema, y la BD lo exige con `CHECK`.
- La unicidad se valida en `verificar_unicidad` (409). El índice único cubre las carreras: `IntegrityError` → 409.

**Soft delete**
- `DELETE` marca `activo=False` y `eliminado_en`, sin borrar la fila.
- Los eliminados no pueden iniciar sesión, devuelven 404 en PATCH y DELETE, y dejan reservados su username y su email.
- Un admin no puede quitarse su rol, desactivarse ni eliminarse (400).

**Rutas**
- Las rutas `/usuarios/me...` deben declararse **antes** que `/usuarios/{usuario_id}`.

**BD compartida**
- Solo se toca la tabla `usuarios`.
- No quitar `version_table` ni `include_object` de `alembic/env.py`: sin ellos, el autogenerate propondría borrar `autos` y `modelos`.
- No crear claves foráneas hacia tablas de otros servicios.

**JWT**
- La clave está solo en el `.env` de la raíz (`JWT_SECRET_KEY`), nunca en `services/api-usuarios/.env`.
- Para cambiar claims, algoritmo o expiración, se modifica `libs/auth-jwt` y se reconstruyen **todos** los servicios.

**Mantenimiento**
- Al cambiar un endpoint, actualizar la carpeta "1. API Usuarios" de `API_Monorepo.postman_collection.json` (raíz), la tabla de arriba y `docs/services/api-usuarios.md`.

## Notas

- El admin inicial (`ADMIN_*` del `.env`) solo se crea si **no existe ningún admin**. Cambiar `ADMIN_PASSWORD` después no modifica nada.
- Las fechas son `timestamptz`. PostgreSQL las devuelve en la zona horaria de su sesión (por ejemplo, `-03:00`).
- Con curl, el login es un **formulario**: `-d "username=...&password=..."`.
