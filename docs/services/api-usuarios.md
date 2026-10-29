# API Usuarios (`services/api-usuarios`)

Servicio de **autenticación** y **gestión de usuarios** del monorepo, hecho con FastAPI:
- Registro de cuentas.
- Login que emite un token **JWT**.
- CRUD de usuarios con roles (`admin` y `usuario`) y borrado lógico (*soft delete*).

El token que emite sirve para todos los servicios del monorepo. Por ejemplo, [`api-autos`](api-autos.md) exige ese token en todas sus rutas.

```
┌──────────────────────── Tu máquina ───────────────────────────────┐
│                                                                   │
│  Cliente ──1. POST /auth/login──►  api-usuarios (127.0.0.1:8001)  │
│     ▲  ◄──── 2. access_token (JWT) ───┘        │                  │
│     │                                          │ tabla usuarios   │
│     └──3. Authorization: Bearer <token>──►  api-autos (:8000)     │
│                                                │ tablas autos,    │
│                                                │ modelos          │
│                                   ┌────────────▼───────────────┐  │
│                                   │ PostgreSQL local :5432     │  │
│                                   │ BD "autos", esquema public │  │
│                                   └────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

Todos los comandos se ejecutan **desde la raíz del monorepo**.

---

## 1. Cómo funciona la autenticación

1. **Registro** (`POST /auth/registro`, público):
   - La contraseña se guarda como **hash Argon2id**, nunca en texto plano.
   - Toda cuenta registrada así tiene rol `usuario`. El campo `rol` no se acepta.
2. **Login** (`POST /auth/login`, público):
   - Se envía un formulario OAuth2 con `username` (o el email) y `password`.
   - Si las credenciales son correctas, responde `{access_token, token_type: "bearer", expires_in}`.
3. **Rutas protegidas**: el cliente envía `Authorization: Bearer <token>`.
   - El token está firmado con `JWT_SECRET_KEY` (HS256) y caduca a los 30 minutos por defecto.
   - Contiene el id, el username y el rol del usuario.

| Código | Significado |
|---|---|
| 401 | No autenticado: falta el token, es inválido o expiró, o el usuario fue desactivado o eliminado. Incluye `WWW-Authenticate: Bearer`. |
| 403 | Autenticado, pero sin permiso (por ejemplo, un usuario normal que intenta listar usuarios). |

### Medidas de seguridad

| Medida | Para qué |
|---|---|
| Argon2id (`pwdlib`) | Hash lento y con sal: resiste la fuerza bruta y las tablas precalculadas |
| Mensaje único `Credenciales incorrectas` | No revela si el usuario existe |
| Verificación contra un hash ficticio si el usuario no existe | El tiempo de respuesta tampoco revela si existe |
| Contraseña de 10 a 128 caracteres, con letras y números | Política mínima; el límite superior evita abusos de CPU |
| `extra="forbid"` en los esquemas | Nadie puede enviar `rol`, `activo` ni `password_hash` donde no corresponde (mass assignment) |
| Respuestas sin `password_hash` | `UsuarioPublic` nunca lo incluye |
| Validación de firma, `exp`, `iss`, `aud` y algoritmo fijo | Impide tokens falsificados, caducados o con `alg: none` |
| Comprobación del usuario en la BD en cada petición | En este servicio, un usuario desactivado pierde el acceso al instante |
| Control de acceso por objeto | Un usuario solo ve su propio perfil por ID (OWASP API1) |
| `Cache-Control: no-store` | Los tokens y datos personales no quedan en cachés |
| Errores 422 saneados | Nunca devuelven lo que envió el cliente, que podría ser una contraseña |

---

## 2. Levantar desde cero

### Requisitos
- Docker Desktop (Docker 24+ con Compose v2).
- PostgreSQL 15+ en tu máquina, con la base de datos `autos`. Es la **misma** que usa `api-autos`; este servicio solo añade la tabla `usuarios`. Si no existe: `psql -h localhost -U postgres -c "CREATE DATABASE autos;"`.

### Paso 1. Configuración

```bash
cd /ruta/al/monorepo
# Clave JWT compartida por todos los servicios
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # pega el resultado en JWT_SECRET_KEY

# Configuración de este servicio
cp services/api-usuarios/.env.example services/api-usuarios/.env
```

Edita `services/api-usuarios/.env`:

```dotenv
DB_HOST=localhost          # docker-compose.yml lo cambia por host.docker.internal
DB_PORT=5432
DB_USER=postgres
DB_DATABASE=autos          # la misma BD que api-autos
DB_PASS=tu_clave

# Administrador inicial (ver "Primer administrador")
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=una-clave-larga-123
```

Ningún `.env` se sube a git ni entra en la imagen de Docker.

### Paso 2. Construir y levantar

```bash
docker compose build api-usuarios
docker compose up -d api-usuarios
docker compose ps                      # debe pasar a "healthy"
docker compose logs -f api-usuarios
```

Al arrancar, el contenedor:
1. Aplica las migraciones (`alembic upgrade head`), que crean la tabla `usuarios`.
2. Crea el administrador inicial si no existe ninguno.
3. Inicia la API.

La API queda en http://127.0.0.1:8001/docs. Pulsa **Authorize** e inicia sesión: Swagger guarda el token y lo envía en cada petición.

Si el puerto 8001 está ocupado: `USUARIOS_PORT=8011 docker compose up -d api-usuarios`.

### Primer administrador

Solo un admin puede crear otros admins, y el registro público siempre crea usuarios normales. Por eso, al arrancar, si en la BD **no hay ningún admin**, se crea uno con `ADMIN_USERNAME`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`.
- Es idempotente: en los siguientes arranques no hace nada.
- La contraseña debe cumplir la misma política que el resto (10 caracteres o más, con letras y números). Si no la cumple, el log lo indica y no se crea el admin.
- La contraseña nunca aparece en los logs.
- Cambiar `ADMIN_PASSWORD` en el `.env` **no** cambia la contraseña de un admin ya creado. Para cambiarla, usa `PUT /usuarios/me/password`.

---

## 3. Endpoints

| Método | Ruta | Acceso | Respuesta | Errores |
|---|---|---|---|---|
| GET | `/` | público | 200 | |
| POST | `/auth/registro` | público | 201 usuario | 409 duplicado, 422 |
| POST | `/auth/login` | público (formulario `username`, `password`) | 200 token | 401 |
| GET | `/usuarios/me` | autenticado | 200 | 401 |
| PATCH | `/usuarios/me` | autenticado (`nombre_completo`, `email`, `username`) | 200 | 401, 409, 422 |
| PUT | `/usuarios/me/password` | autenticado (`password_actual`, `password_nueva`) | 204 | 400 actual incorrecta, 401, 422 |
| POST | `/usuarios` | admin (puede fijar `rol`) | 201 | 401, 403, 409, 422 |
| GET | `/usuarios?skip&limit&q&rol&activo` | admin | 200 página | 401, 403, 422 |
| GET | `/usuarios/{id}` | admin o el propio usuario | 200 | 401, 403, 404 |
| PATCH | `/usuarios/{id}` | admin (datos, `rol`, `activo`, `password`) | 200 | 400, 401, 403, 404, 409, 422 |
| DELETE | `/usuarios/{id}` | admin (soft delete) | 204 | 400, 401, 403, 404 |

Notas:
- **Listados**: devuelven `{total, skip, limit, items}`. `limit` va de 1 a 100. `q` busca en el username o el email (contiene). `activo=false` muestra los desactivados y los eliminados.
- **`username` y `email`** se guardan en minúsculas. El username admite de 3 a 30 caracteres: letras, números y `.`, `_`, `-` entre palabras.
- **PATCH** solo cambia los campos enviados, y un campo enviado no puede ser `null`. Si el admin envía `password`, se **vuelve a hashear** antes de guardarla.
- **Un admin no puede** quitarse a sí mismo el rol de admin, desactivarse ni eliminarse (400). Así el sistema no se queda sin administradores.

### Soft delete

`DELETE /usuarios/{id}` no borra la fila: pone `activo=false` y guarda la fecha en `eliminado_en`.
- El usuario ya no puede iniciar sesión.
- Su token deja de funcionar al instante **en este servicio**. En `api-autos`, que no consulta la BD, sigue funcionando hasta que expira.
- Su username y su email siguen **reservados**: nadie puede registrarse con ellos (409).
- Un admin puede verlo con `GET /usuarios/{id}`. Borrarlo otra vez responde 404.

Para desactivar a alguien de forma temporal, sin eliminarlo, usa `PATCH /usuarios/{id}` con `{"activo": false}` y luego `{"activo": true}`.

---

## 4. Probar

### Postman / newman
1. Importa `services/api-usuarios/postman/API_Usuarios.postman_collection.json`.
2. En las variables de la colección, pon en `adminPassword` tu `ADMIN_PASSWORD`.
3. Ejecuta la colección completa. Son 41 peticiones que cubren registro, login, perfil, cambio de contraseña, permisos (401 y 403), administración y soft delete. Además, en **cada** respuesta se comprueba que no aparezcan contraseñas ni hashes.

```bash
npx -y newman run services/api-usuarios/postman/API_Usuarios.postman_collection.json \
  --env-var adminPassword=TU_CLAVE_ADMIN
```

Cada ejecución usa usuarios con un sufijo único (`runId`), porque los usuarios eliminados dejan reservados su username y su email.

### A mano con curl

```bash
# Registro
curl -X POST http://127.0.0.1:8001/auth/registro -H "Content-Type: application/json" \
  -d '{"username":"ana","email":"ana@example.com","nombre_completo":"Ana Pérez","password":"Clave-Segura-2026"}'

# Login (formulario, no JSON)
curl -X POST http://127.0.0.1:8001/auth/login -d "username=ana&password=Clave-Segura-2026"

# Ruta protegida
curl -H "Authorization: Bearer <access_token>" http://127.0.0.1:8001/usuarios/me
```

---

## 5. Migraciones y base de datos compartida

La BD `autos` la comparten dos servicios. Cada uno es dueño de sus tablas y tiene su propio historial de Alembic:

| Servicio | Tablas | Tabla de versiones de Alembic |
|---|---|---|
| `api-autos` | `autos`, `modelos` | `alembic_version` |
| `api-usuarios` | `usuarios` | `alembic_version_usuarios` |

En `alembic/env.py`, cada servicio ignora las tablas que no son suyas (`include_object`). Así, el autogenerate de un servicio nunca propone borrar las tablas del otro. Tampoco hay claves foráneas entre tablas de servicios distintos.

```bash
docker compose exec api-usuarios alembic current
docker compose exec api-usuarios alembic check          # ¿hay cambios sin migrar?

# Nueva migración tras cambiar app/models.py
docker compose build api-usuarios
docker compose run --rm -v "$(pwd)/services/api-usuarios/alembic/versions:/app/alembic/versions" \
  api-usuarios alembic revision --autogenerate --rev-id 0002 -m "descripcion"
docker compose up -d --build api-usuarios

# Borrar todos los usuarios (solo la tabla usuarios). Al reiniciar se recrea el admin inicial.
docker compose exec api-usuarios alembic downgrade base
docker compose exec api-usuarios alembic upgrade head
docker compose restart api-usuarios
```

---

## 6. Solución de problemas

| Síntoma | Solución |
|---|---|
| `Define JWT_SECRET_KEY en el .env de la raíz` | Crea el `.env` de la raíz desde `.env.example` y genera la clave. |
| El contenedor se reinicia y el log menciona `jwt_secret_key` | La clave tiene menos de 32 caracteres. |
| Los logs dicen `ADMIN_* no válido (password)` | `ADMIN_PASSWORD` no cumple la política (10 o más caracteres, con letras y números). |
| No puedo iniciar sesión como admin | ¿Ya existía un admin? El `.env` solo se usa la primera vez. Revisa con `docker compose logs api-usuarios \| grep Administrador`. |
| El token funciona en `api-usuarios` pero `api-autos` responde 401 | Los dos servicios no tienen la misma `JWT_SECRET_KEY`: reinícialos con `docker compose up -d`. |
| 401 tras un rato | El token expiró (30 minutos por defecto, `JWT_MINUTOS_EXPIRACION`). Vuelve a iniciar sesión. |
| 409 al registrar un usuario "nuevo" | El username o el email pertenecen a otro usuario, aunque esté eliminado (soft delete). |
| 422 en `/auth/login` | El login es un **formulario** (`-d "username=...&password=..."`), no JSON. |

---

## Estructura

```
.env                                 (raíz) JWT_SECRET_KEY compartida
docker-compose.yml                   (raíz) servicio "api-usuarios" (puerto 8001)
libs/auth-jwt/                       emisión y validación de JWT (ver docs/libs/auth-jwt.md)
services/api-usuarios/
├── Dockerfile, Dockerfile.dockerignore, docker/entrypoint.sh
├── .env.example, requirements.txt
├── alembic.ini, alembic/            migraciones (tabla de versiones: alembic_version_usuarios)
├── app/
│   ├── config.py                    BD, admin inicial, CORS
│   ├── models.py                    tabla usuarios
│   ├── schemas.py                   DTOs; UsuarioPublic sin password_hash
│   ├── seguridad.py                 Argon2id
│   ├── servicios.py                 crear usuario, unicidad
│   ├── dependencies.py              guards: obtener_usuario_actual (401), requiere_admin (403)
│   ├── routers/auth.py, usuarios.py
│   └── main.py                      lifespan (admin inicial), CORS, cabeceras, errores
├── postman/API_Usuarios.postman_collection.json
└── CLAUDE.md
```
