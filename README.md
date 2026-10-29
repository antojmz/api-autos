# api-autos — Monorepo

Monorepo del proyecto Concesionario de Autos: backends, frontend y librerías compartidas en un solo repositorio.

```
.
├── services/
│   ├── api-usuarios/    Autenticación (JWT) y CRUD de usuarios
│   └── api-autos/       API REST de autos y modelos (requiere token)
├── apps/
│   └── web/             Frontend Nuxt 4 + Vuetify 4 (BFF con cookie httpOnly)
├── libs/
│   └── auth-jwt/        Librería compartida de JWT
├── docs/                Toda la documentación
└── docker-compose.yml   Levanta los servicios del monorepo
```

## Levantar la aplicación desde cero

La aplicación tiene tres contenedores Docker (`web`, `api-usuarios` y `api-autos`) que usan el **PostgreSQL instalado en tu máquina**. No necesitas Python ni entornos virtuales: todo se construye dentro de las imágenes.

```
navegador ──► web :3000 ──► api-usuarios :8001 ─┐
                       └──► api-autos    :8000 ─┴─► PostgreSQL de tu máquina (BD "autos")
```

Todos los comandos se ejecutan **desde la raíz del repositorio**.

### 0. Requisitos

| Requisito | Para qué | Cómo comprobarlo |
|---|---|---|
| Git | Clonar el repositorio | `git --version` |
| Docker Desktop 24+ (con Compose v2) | Construir y ejecutar los servicios | `docker --version` y `docker compose version` |
| PostgreSQL 15+ en `localhost:5432` | Guardar los datos | `pg_isready -h localhost -p 5432` |
| Puertos 3000, 8000 y 8001 libres | web, api-autos y api-usuarios | `lsof -nP -iTCP:3000 -sTCP:LISTEN` (repite con 8000 y 8001; no debe mostrar nada) |
| *(Opcional)* Node.js 24.15+ | Ejecutar las pruebas con `npx newman` o desarrollar el frontend | `node --version` |

### 1. Clonar el repositorio

```bash
git clone https://github.com/antojmz/api-autos.git
cd api-autos
```

### 2. Crear la base de datos

```bash
psql -h localhost -U postgres -c "CREATE DATABASE autos;"
```

`psql` te pedirá la contraseña del usuario `postgres`. Si ya existe la base de datos, verás `database "autos" already exists`, y puedes continuar.

Solo hace falta la base de datos **vacía**. Las tablas (`autos`, `modelos` y `usuarios`) las crean las migraciones de Alembic al arrancar los contenedores. Las dos APIs comparten esta base de datos, pero cada una gestiona solo sus propias tablas.

### 3. Configurar los tres archivos `.env`

Ningún `.env` se sube a git ni se copia dentro de las imágenes.

**a) Raíz: clave para firmar los tokens JWT**, compartida por las dos APIs. Este comando copia el ejemplo y genera una clave aleatoria:

```bash
cp .env.example .env
sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env && rm .env.bak
```

**b) `services/api-usuarios/.env`: base de datos y administrador inicial.**

```bash
cp services/api-usuarios/.env.example services/api-usuarios/.env
```

Edítalo y cambia, como mínimo:

```dotenv
DB_PASS=la_clave_de_tu_usuario_postgres

# Administrador que se crea solo en el primer arranque (si no existe ningún admin).
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=una-clave-propia-2026     # 10 a 128 caracteres, con letras y números
```

**c) `services/api-autos/.env`: base de datos.**

```bash
cp services/api-autos/.env.example services/api-autos/.env
```

Edítalo y pon tu `DB_PASS`.

En los dos `.env` de los servicios, deja `DB_HOST=localhost`. Dentro de un contenedor, `localhost` es el propio contenedor, así que `docker-compose.yml` lo cambia automáticamente por `host.docker.internal`, que es como los contenedores llegan a tu máquina.

### 4. Construir las imágenes

```bash
docker compose build
```

Construye `api-usuarios`, `api-autos` y `web`. La primera vez tarda unos minutos porque descarga las imágenes base e instala las dependencias.

### 5. Levantar los servicios

```bash
docker compose up -d
```

Al arrancar:
1. **api-usuarios** y **api-autos** aplican sus migraciones (`alembic upgrade head`), que crean las tablas.
2. **api-usuarios** crea el administrador inicial con los datos de su `.env`.
3. **web** espera a que las dos APIs estén sanas (`healthy`) y después arranca.

Comprueba que todo está bien. Tarda unos 30 a 60 segundos:

```bash
docker compose ps                                              # los tres deben mostrar "(healthy)"
docker compose logs api-usuarios | grep "Administrador inicial"  # "Administrador inicial 'admin' creado"
```

### 6. Usar la aplicación

| Servicio | URL | Cómo entrar |
|---|---|---|
| **web** | **http://127.0.0.1:3000** | Con `ADMIN_USERNAME` y `ADMIN_PASSWORD`, o creando una cuenta en "Regístrate" |
| api-usuarios | http://127.0.0.1:8001/docs | Botón **Authorize**: usuario y contraseña |
| api-autos | http://127.0.0.1:8000/docs | Botón **Authorize**: pega un token obtenido en api-usuarios (`POST /auth/login`) |

Con el admin puedes gestionar autos, modelos y usuarios. Un usuario registrado puede crear y editar autos y modelos, pero no eliminarlos ni administrar usuarios.

### 7. *(Opcional)* Comprobar que todo funciona

Ejecuta la colección de Postman de la raíz (ver [Probar las APIs](#probar-las-apis)). Deben pasar las 104 peticiones.

### Operación diaria

| Acción | Comando |
|---|---|
| Ver los logs de un servicio | `docker compose logs -f web` (o `api-usuarios`, `api-autos`) |
| Detener todo (los datos siguen en PostgreSQL) | `docker compose down` |
| Volver a levantar | `docker compose up -d` |
| **Aplicar cambios de código** | `docker compose up -d --build` |
| Vaciar la base de datos y empezar de cero | `docker compose exec api-autos alembic downgrade base && docker compose exec api-autos alembic upgrade head`, lo mismo con `api-usuarios`, y luego `docker compose restart api-usuarios` (recrea el admin) |

### Si un puerto está ocupado

```bash
AUTOS_PORT=8002 USUARIOS_PORT=8011 WEB_PORT=3001 docker compose up -d
```

Solo cambian los puertos de **tu máquina**. La web habla con las APIs por la red interna de Docker, así que cambiar los puertos de las APIs no la afecta.

### Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `Define JWT_SECRET_KEY en el .env de la raíz` | Falta el `.env` de la raíz: repite el paso 3a. |
| Un contenedor se reinicia una y otra vez | Mira el motivo con `docker compose logs <servicio>`. Normalmente es la conexión a PostgreSQL (ver las filas siguientes). |
| `connection refused` hacia `host.docker.internal` | PostgreSQL no está corriendo (`pg_isready -h localhost`) o solo escucha en localhost: pon `listen_addresses = '*'` en `postgresql.conf` y reinícialo. |
| `no pg_hba.conf entry for host ...` | PostgreSQL rechaza la IP de Docker. Añade esa IP o su red a `pg_hba.conf` (ver [docs/services/api-autos.md](docs/services/api-autos.md#5-solución-de-problemas)). |
| `password authentication failed` | Revisa `DB_USER` y `DB_PASS` en los `.env` de los servicios y vuelve a ejecutar `docker compose up -d`. |
| `database "autos" does not exist` | Repite el paso 2. |
| No aparece "Administrador inicial ... creado" | `ADMIN_PASSWORD` no cumple la política (el log dice `ADMIN_* no válido`), o ya existía un admin en la base de datos. |
| Inicias sesión en la web y vuelve a `/login` | La cookie de sesión tiene `Secure` sin HTTPS: no definas `WEB_COOKIE_SECURE=true` en local. |
| `bind: address already in use` | Un puerto está ocupado: ver [Si un puerto está ocupado](#si-un-puerto-está-ocupado). |

Cada guía de `docs/` tiene su propia tabla de solución de problemas con más casos.

## Desarrollo con `just` (recarga en caliente)

Para desarrollar, el [`justfile`](justfile) levanta las APIs y el frontend en **modo desarrollo**. El código de tu máquina se monta dentro de los contenedores y cada servicio se recompila solo al guardar un archivo. No hace falta reconstruir imágenes ni tener Python o Node instalados localmente.

```bash
brew install just      # una sola vez (Linux/Windows: https://just.systems)
just setup             # crea los .env que falten (y genera JWT_SECRET_KEY); luego edita DB_PASS y ADMIN_*
just dev               # levanta todo en modo desarrollo, con logs en vivo (Ctrl+C para detener)
```

| Qué cambias | Qué pasa |
|---|---|
| Código Python de `services/*/app/` | uvicorn recarga la API en 1 o 2 segundos |
| `libs/auth-jwt/` | Se recargan las dos APIs |
| Páginas, componentes o el BFF en `apps/web/` | Nuxt recompila; en el navegador el cambio aparece solo (HMR) |
| Una migración nueva | `just migrate` (sin reiniciar) |
| `requirements.txt`, `package.json`, Dockerfile o `docker-compose*.yml` | Vuelve a ejecutar `just dev` |

Tareas disponibles (`just` sin argumentos las lista):

| Tarea | Para qué |
|---|---|
| `just setup` | Crear los `.env` que falten (nunca sobrescribe) |
| `just dev` / `just dev-d` | Modo desarrollo, en primer plano o en segundo plano |
| `just up` | Modo producción (imágenes compiladas, como en el paso 5) |
| `just down` | Detener todo, en cualquiera de los dos modos |
| `just ps` / `just logs [servicio]` | Estado / logs (`just logs api-autos`) |
| `just shell <servicio>` | Terminal dentro de un contenedor |
| `just migrate [servicio]` | Aplicar migraciones pendientes |
| `just migration <servicio> <rev> "<mensaje>"` | Generar una migración (`just migration api-autos 0002 "agregar color"`) |
| `just test ["carpeta"]` | Ejecutar la colección de Postman (requiere Node para `npx`) |
| `just typecheck` | Comprobar los tipos del frontend (con `just dev` en marcha) |
| `just build` | Construir las imágenes de producción |

Los puertos se cambian igual que con Compose: `AUTOS_PORT=8002 just dev`.

En desarrollo, el frontend corre en el contenedor `web-dev` (`nuxt dev`) en lugar de `web`. Usa los mismos puertos, así que no se pueden tener los dos a la vez: `just dev` quita el de producción y `just up` quita el de desarrollo. Los detalles están en [`docker-compose.dev.yml`](docker-compose.dev.yml).

## Probar las APIs

La colección de Postman `API_Monorepo.postman_collection.json` (raíz) prueba todo el monorepo: **api-usuarios**, **api-autos** y el **BFF** de la web. Son 104 peticiones con sus tests.

Impórtala en Postman y pon en la variable `adminPassword` tu `ADMIN_PASSWORD`, o ejecútala desde la terminal:

```bash
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --env-var "adminPassword=$PW"
```

## Documentación

Toda la documentación está en [`docs/`](docs/README.md):
- [Arquitectura del monorepo](docs/arquitectura.md)
- [Backend `api-usuarios`: autenticación y usuarios](docs/services/api-usuarios.md)
- [Backend `api-autos`: instalación, operación y solución de problemas](docs/services/api-autos.md)
- [Frontend `web` (Nuxt 4 + Vuetify 4)](docs/apps/web.md)
- [Librería `auth-jwt`](docs/libs/auth-jwt.md)
- [Versionado y releases (release-please)](docs/releases.md): los commits siguen Conventional Commits (`feat:`, `fix:`...)
