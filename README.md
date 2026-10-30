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
├── docker-compose.yml       Servicios (modo producción: imágenes compiladas)
├── docker-compose.dev.yml   Overrides de desarrollo (código montado + recarga en caliente)
└── justfile                 Tareas con `just` (just dev, just up, just test...)
```

La aplicación son tres servicios (`web`, `api-usuarios` y `api-autos`) que usan el **PostgreSQL instalado en la máquina**:

```
navegador ──► web :3000 ──► api-usuarios :8001 ─┐
                       └──► api-autos    :8000 ─┴─► PostgreSQL (BD "autos")
```

Todos los comandos se ejecutan **desde la raíz del repositorio**, salvo que se indique otra cosa.

---

## ¿Qué camino elijo?

Hay cuatro formas de levantar el proyecto. Todas empiezan por la misma [preparación común](#preparación-común-todos-los-caminos).

| # | Camino | Para qué | Necesitas | Comando principal |
|---|---|---|---|---|
| 1 | [Docker + `npm run dev`](#camino-1-apis-en-docker--frontend-con-npm-run-dev) | Desarrollar, con el frontend en tu máquina (tu editor y Node local) | Docker, Node 24.15+ | APIs en Docker + `npm run dev` |
| 2 | [`just` para desarrollo](#camino-2-desarrollo-local-con-just) | Desarrollar con **todo** en Docker; no necesitas Node ni Python | Docker, `just` | `just dev` |
| 3 | [`just` para producción](#camino-3-producción-con-just) | Desplegar en un servidor real | Docker, `just`, proxy HTTPS | `just up` |
| 4 | [Solo Docker](#camino-4-solo-docker) | Probar o desplegar sin instalar nada más | Docker | `docker compose up -d --build` |

En los caminos 1 y 2, **las APIs y el frontend se recargan solos al guardar un archivo**. En los caminos 3 y 4 las imágenes llevan una copia del código, y cada cambio requiere reconstruir.

---

## Preparación común (todos los caminos)

### Paso 0. Requisitos

| Requisito | Camino | Cómo comprobarlo |
|---|---|---|
| Git | todos | `git --version` |
| Docker 24+ con Compose v2 (Docker Desktop en Mac/Windows) | todos | `docker --version` y `docker compose version` |
| PostgreSQL 15+ en `localhost:5432` | todos | `pg_isready -h localhost -p 5432` |
| `just` | 2 y 3 | `just --version` (instalar: `brew install just`, o ver [just.systems](https://just.systems)) |
| Node.js 24.15+ | 1 (y para `just test` / newman) | `node --version` |
| Puertos 3000, 8000 y 8001 libres | todos | `lsof -nP -iTCP:3000 -sTCP:LISTEN` (repite con 8000 y 8001; no debe mostrar nada) |

### Paso 1. Clonar el repositorio

```bash
git clone https://github.com/antojmz/api-autos.git
cd api-autos
```

### Paso 2. Crear la base de datos

```bash
psql -h localhost -U postgres -c "CREATE DATABASE autos;"
```

`psql` te pedirá la contraseña del usuario `postgres`. Si la base ya existe, verás `database "autos" already exists` y puedes continuar.

Solo hace falta la base **vacía**. Las tablas (`autos`, `modelos` y `usuarios`) las crean las migraciones de Alembic al arrancar las APIs. Las dos APIs comparten esta base de datos y cada una gestiona solo sus tablas.

### Paso 3. Configurar los archivos `.env`

Ningún `.env` se sube a git ni se copia dentro de las imágenes.

**Opción rápida (con `just`)**: crea los que falten y genera la clave JWT:

```bash
just setup
```

**Opción manual**:

```bash
# a) Raíz: clave para firmar los tokens JWT (compartida por las dos APIs)
cp .env.example .env
sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env && rm .env.bak

# b) y c) Configuración de cada API
cp services/api-usuarios/.env.example services/api-usuarios/.env
cp services/api-autos/.env.example services/api-autos/.env
```

En cualquiera de las dos opciones, **edita** después:

| Archivo | Qué cambiar |
|---|---|
| `services/api-usuarios/.env` | `DB_PASS`, y el administrador inicial: `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (de 10 a 128 caracteres, con letras y números) |
| `services/api-autos/.env` | `DB_PASS` |

Deja `DB_HOST=localhost`. Dentro de un contenedor, `localhost` es el propio contenedor, así que Docker Compose lo cambia automáticamente por `host.docker.internal`, que es como los contenedores llegan a tu máquina.

El administrador inicial se crea solo en el primer arranque, si en la base no hay ningún admin.

### Paso 4. *(Para quien va a hacer commits)* Instalar los hooks de pre-commit

Antes de cada `git commit`, [pre-commit](https://pre-commit.com) revisa automáticamente lo que vas a subir:

| Revisión | Qué hace |
|---|---|
| Higiene de archivos | Quita espacios finales, añade el salto de línea final, valida YAML, JSON y TOML, y detecta restos de conflictos de merge, archivos de más de 1 MB y claves privadas |
| **Secretos** ([gitleaks](https://github.com/gitleaks/gitleaks)) | Bloquea el commit si encuentra tokens, contraseñas o claves (por ejemplo, el contenido de un `.env` pegado por error) |
| **Python** ([Ruff](https://docs.astral.sh/ruff/)) | Lint y formato de `services/` y `libs/` (configuración en `ruff.toml`) |
| **Mensaje del commit** | Debe seguir Conventional Commits (`feat(api-autos): ...`, `fix: ...`), porque release-please calcula la versión con él. Los `Merge branch ...` se aceptan |

```bash
brew install pre-commit      # una vez (alternativa: pipx install pre-commit)
just hooks                   # instala los hooks en este clon (just setup también lo hace)
# sin just:  pre-commit install --install-hooks
```

- **Si un hook corrige algo** (formato o espacios), el commit se detiene: revisa los cambios con `git diff`, vuelve a hacer `git add` y repite el commit.
- **Revisar todo el repositorio a mano**: `just lint` (o `pre-commit run --all-files`).
- **Saltar los hooks** (`git commit --no-verify`) está desaconsejado, porque se pierde la protección contra secretos.

---

## Camino 1: APIs en Docker + frontend con `npm run dev`

Las APIs corren en Docker con **recarga automática** (su código está montado en el contenedor) y el frontend corre en tu máquina con `npm run dev` (**HMR**: los cambios aparecen en el navegador sin recargar la página).

**1.1 Levanta las APIs en modo desarrollo**. Solo las dos APIs, no la web:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build api-usuarios api-autos
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps    # las dos en "(healthy)"
```

**1.2 Arranca el frontend** en otra terminal:

```bash
cd apps/web
cp .env.example .env     # solo la primera vez: apunta a las APIs en 127.0.0.1:8000 y :8001
npm install              # solo la primera vez o cuando cambie package.json
npm run dev
```

**1.3 Abre http://localhost:3000**. Usa `localhost` y no `127.0.0.1`: en macOS, `nuxt dev` escucha en `localhost`. Inicia sesión con el admin del `.env`.

| Qué cambias | Qué pasa |
|---|---|
| `services/*/app/` o `libs/auth-jwt/` | La API se reinicia sola en 1 o 2 segundos (verás `WatchFiles detected changes` en `docker compose ... logs -f api-autos`) |
| `apps/web/` (páginas, componentes, BFF) | Nuxt recompila al instante y el navegador se actualiza (HMR) |
| `requirements.txt` | Vuelve a ejecutar el comando del paso 1.1 (reconstruye) |
| `package.json` | `npm install` y vuelve a ejecutar `npm run dev` |

**Detener**: `Ctrl+C` en la terminal del frontend, y para las APIs:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Ten en cuenta:
- **Puerto 3000 ocupado**: si están levantados `web` (caminos 3 y 4) o `web-dev` (camino 2), usan el puerto 3000. Detenlos antes o usa `npm run dev -- --port 3001`.
- **Versión de Node**: Nuxt 4.6 pide Node 24.15 o superior. Con 24.14, `npm install` muestra el aviso `EBADENGINE` pero funciona. Si algo falla, actualiza con `nvm install 24`.
- **No mezclar caminos**: no ejecutes los caminos 1 y 2 a la vez, porque comparten el puerto 3000 y la carpeta `apps/web/.nuxt`.

---

## Camino 2: desarrollo local con `just`

Todo corre en Docker con recarga en caliente: las APIs con uvicorn `--reload` y el frontend en el contenedor `web-dev`, con `nuxt dev` y HMR. No necesitas Python ni Node instalados.

**2.1 Instala `just`** (una vez):

```bash
brew install just
```

**2.2 Prepara los `.env`** (si no lo hiciste en el paso 3) y edítalos:

```bash
just setup
```

**2.3 Levanta todo**:

```bash
just dev          # en primer plano, con los logs de todos los servicios (Ctrl+C para detener)
# o
just dev-d        # en segundo plano
```

**2.4 Abre http://127.0.0.1:3000**. Las APIs están en http://127.0.0.1:8001/docs y http://127.0.0.1:8000/docs.

| Qué cambias | Qué pasa |
|---|---|
| Código Python de `services/*/app/` | uvicorn recarga la API en 1 o 2 segundos |
| `libs/auth-jwt/` | Se recargan las dos APIs |
| Páginas, componentes o el BFF en `apps/web/` | Nuxt recompila; en el navegador el cambio aparece solo (HMR) |
| Una migración nueva | `just migrate` (sin reiniciar) |
| `requirements.txt`, `package.json`, Dockerfile o `docker-compose*.yml` | Vuelve a ejecutar `just dev` |

Tareas del día a día (`just` sin argumentos las lista todas):

| Tarea | Para qué |
|---|---|
| `just ps` / `just logs [servicio]` | Estado / logs en vivo (`just logs api-autos`) |
| `just shell <servicio>` | Abrir una terminal dentro de un contenedor |
| `just migrate [servicio]` | Aplicar las migraciones pendientes |
| `just migration <servicio> <rev> "<mensaje>"` | Generar una migración (`just migration api-autos 0002 "agregar color"`) |
| `just test ["carpeta"]` | Ejecutar la colección de Postman (requiere Node para `npx`) |
| `just typecheck` | Comprobar los tipos del frontend (con `just dev` en marcha) |
| `just down` | Detener todo |

---

## Camino 3: producción con `just`

Para desplegar en un **servidor** (Linux con Docker). Usa las imágenes compiladas, sin código montado ni recarga.

### 3.1 Preparar el servidor

1. Instala **Docker Engine** con Compose v2, **`just`** y **PostgreSQL 15+**.
2. Configura PostgreSQL para aceptar conexiones de los contenedores. En Linux, `host.docker.internal` apunta al host a través de la red de Docker:

   ```conf
   # postgresql.conf: escuchar también en la interfaz de Docker
   listen_addresses = 'localhost,172.17.0.1'

   # pg_hba.conf: permitir las redes de Docker (172.16.0.0/12)
   host  autos  usuario_app  172.16.0.0/12  scram-sha-256
   ```

   Después, `sudo systemctl restart postgresql`.
3. **No expongas el puerto 5432 a Internet**: ciérralo en el firewall.
4. Crea un **usuario de BD propio** para la aplicación, en lugar de usar `postgres`, y la base de datos:

   ```bash
   sudo -u postgres psql -c "CREATE USER usuario_app WITH PASSWORD 'una-clave-larga';"
   sudo -u postgres psql -c "CREATE DATABASE autos OWNER usuario_app;"
   ```

### 3.2 Código y configuración

```bash
git clone https://github.com/antojmz/api-autos.git && cd api-autos
git checkout v1.1.0          # despliega una versión publicada (ver las Releases en GitHub)
just setup                   # crea los .env y genera JWT_SECRET_KEY
```

Antes de arrancar, revisa esta **checklist de producción**:

- [ ] `.env` de la raíz: `JWT_SECRET_KEY` generada por `just setup` (única para este servidor).
- [ ] `.env` de la raíz: añade **`WEB_COOKIE_SECURE=true`**, para que la cookie de sesión solo viaje por HTTPS.
- [ ] `services/*/.env`: `DB_USER=usuario_app` y su `DB_PASS`.
- [ ] `services/api-usuarios/.env`: `ADMIN_PASSWORD` robusta. **Cámbiala desde la web** (Mi perfil) tras el primer inicio de sesión.

### 3.3 Construir y levantar

```bash
just up                                   # construye las imágenes y levanta todo en segundo plano
just ps                                   # los tres servicios en "(healthy)"
just logs api-usuarios                    # debe aparecer "Administrador inicial 'admin' creado"
```

Los contenedores tienen `restart: unless-stopped`: si el servidor se reinicia, vuelven a arrancar solos (con Docker configurado para arrancar con el sistema).

### 3.4 HTTPS con un proxy inverso

Los puertos se publican **solo en `127.0.0.1`**, así que la aplicación no es accesible desde fuera hasta que pongas un proxy inverso con HTTPS delante de la web. Las APIs no se publican: la web habla con ellas por la red interna de Docker.

Ejemplo con [Caddy](https://caddyserver.com), que obtiene y renueva el certificado solo:

```caddy
# /etc/caddy/Caddyfile
concesionario.ejemplo.com {
    reverse_proxy 127.0.0.1:3000
}
```

Con nginx, el equivalente es un `server` con `listen 443 ssl` y `proxy_pass http://127.0.0.1:3000;`, con el certificado de Let's Encrypt (certbot).

### 3.5 Actualizar a una nueva versión

```bash
pg_dump -h localhost -U usuario_app -Fc autos > backup-$(date +%F).dump   # 1. copia de seguridad
git fetch --tags && git checkout v1.2.0                                     # 2. nueva versión
just up                                                                     # 3. reconstruye y reinicia
```

Las migraciones de base de datos se aplican solas al arrancar las APIs.

### 3.6 Copias de seguridad y restauración

```bash
pg_dump -h localhost -U usuario_app -Fc autos > backup.dump                        # copia
pg_restore -h localhost -U usuario_app -d autos --clean --if-exists backup.dump    # restaurar
```

### 3.7 Operación

| Acción | Comando |
|---|---|
| Estado | `just ps` |
| Logs | `just logs` (o `just logs web`) |
| Reiniciar un servicio | `docker compose restart api-autos` |
| Detener todo | `just down` |

---

## Camino 4: solo Docker

Sin `just` ni Node: solo Docker Compose, con las imágenes compiladas. Sirve para probar el proyecto en tu máquina o para desplegar en un servidor; en ese caso, sigue además los apartados 3.1, 3.4, 3.5 y 3.6 del camino 3.

**4.1 Construir las imágenes** (`api-usuarios`, `api-autos` y `web`; la primera vez tarda unos minutos):

```bash
docker compose build
```

**4.2 Levantar**:

```bash
docker compose up -d
```

Al arrancar:
1. Las APIs aplican sus migraciones (`alembic upgrade head`).
2. `api-usuarios` crea el administrador inicial.
3. `web` espera a que las dos APIs estén sanas (`healthy`) y después arranca.

**4.3 Comprobar** (tarda unos 30 a 60 segundos):

```bash
docker compose ps                                                # los tres en "(healthy)"
docker compose logs api-usuarios | grep "Administrador inicial"  # "Administrador inicial 'admin' creado"
```

**4.4 Usar la aplicación**:

| Servicio | URL | Cómo entrar |
|---|---|---|
| **web** | **http://127.0.0.1:3000** | Con `ADMIN_USERNAME` y `ADMIN_PASSWORD`, o creando una cuenta en "Regístrate" |
| api-usuarios | http://127.0.0.1:8001/docs | Botón **Authorize**: usuario y contraseña |
| api-autos | http://127.0.0.1:8000/docs | Botón **Authorize**: pega un token obtenido en api-usuarios (`POST /auth/login`) |

**Operación**:

| Acción | Comando |
|---|---|
| Logs | `docker compose logs -f web` (o `api-usuarios`, `api-autos`) |
| Detener (los datos siguen en PostgreSQL) | `docker compose down` |
| **Aplicar cambios de código** | `docker compose up -d --build` |
| Migraciones | `docker compose exec api-autos alembic upgrade head` (igual con `api-usuarios`) |
| Vaciar la base de datos | `docker compose exec api-autos alembic downgrade base && docker compose exec api-autos alembic upgrade head`, lo mismo con `api-usuarios`, y luego `docker compose restart api-usuarios` (recrea el admin) |

¿Quieres recarga en caliente sin `just`? Usa los dos archivos de Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

---

## Resumen de comandos por camino

| Acción | 1. Docker + npm | 2. `just` desarrollo | 3. `just` producción | 4. Solo Docker |
|---|---|---|---|---|
| Levantar | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build api-usuarios api-autos` + `npm run dev` | `just dev` | `just up` | `docker compose up -d --build` |
| Detener | `Ctrl+C` + `docker compose -f docker-compose.yml -f docker-compose.dev.yml down` | `just down` (o `Ctrl+C`) | `just down` | `docker compose down` |
| Logs | `docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f` | `just logs` | `just logs` | `docker compose logs -f` |
| Aplicar cambios de código | automático | automático | `just up` | `docker compose up -d --build` |
| Migraciones nuevas | `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api-autos alembic upgrade head` | `just migrate` | `just migrate` | `docker compose exec api-autos alembic upgrade head` |
| URL de la web | http://localhost:3000 | http://127.0.0.1:3000 | tu dominio (HTTPS) | http://127.0.0.1:3000 |

---

## Si un puerto está ocupado

Los puertos del host se cambian con variables de entorno en todos los caminos:

```bash
AUTOS_PORT=8002 USUARIOS_PORT=8011 WEB_PORT=3001 just dev            # o just up
AUTOS_PORT=8002 USUARIOS_PORT=8011 WEB_PORT=3001 docker compose up -d
```

Solo cambian los puertos de **tu máquina**. La web en Docker habla con las APIs por la red interna, así que cambiar los puertos de las APIs no la afecta. En el camino 1, ajusta `NUXT_API_*_URL` en `apps/web/.env` si cambias `AUTOS_PORT` o `USUARIOS_PORT`.

## Probar las APIs

La colección de Postman `API_Monorepo.postman_collection.json` (raíz) prueba todo el monorepo: **api-usuarios**, **api-autos** y el **BFF** de la web. Son 104 peticiones con sus tests.

Impórtala en Postman y pon en la variable `adminPassword` tu `ADMIN_PASSWORD`, o ejecútala desde la terminal:

```bash
just test
# sin just:
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --env-var "adminPassword=$PW"
```

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `Define JWT_SECRET_KEY en el .env de la raíz` | Falta el `.env` de la raíz: repite el paso 3. |
| Un contenedor se reinicia una y otra vez | Mira el motivo con `docker compose logs <servicio>`. Normalmente es la conexión a PostgreSQL (ver las filas siguientes). |
| `connection refused` hacia `host.docker.internal` | PostgreSQL no está corriendo (`pg_isready -h localhost`) o no escucha en la interfaz de Docker: revisa `listen_addresses` (apartado 3.1) y reinícialo. |
| `no pg_hba.conf entry for host ...` | PostgreSQL rechaza la IP de Docker. Añade `172.16.0.0/12` (o la IP del error) a `pg_hba.conf` (apartado 3.1). |
| `password authentication failed` | Revisa `DB_USER` y `DB_PASS` en los `.env` de los servicios y vuelve a levantar. |
| `database "autos" does not exist` | Repite el paso 2. |
| No aparece "Administrador inicial ... creado" | `ADMIN_PASSWORD` no cumple la política (el log dice `ADMIN_* no válido`), o ya existía un admin en la base de datos. |
| Inicias sesión en la web y vuelve a `/login` | La cookie tiene `Secure` sin HTTPS: en local no definas `WEB_COOKIE_SECURE=true`. En producción, accede por `https://`. |
| `bind: address already in use` | Un puerto está ocupado: ver [Si un puerto está ocupado](#si-un-puerto-está-ocupado). |
| Camino 1: `localhost:3000` no responde con `127.0.0.1` | `nuxt dev` escucha en `localhost`: usa http://localhost:3000. |
| Camino 1: `EBADENGINE` al hacer `npm install` | Tu Node es anterior a 24.15. Normalmente funciona igual; si falla, ejecuta `nvm install 24`. |
| Producción: el dominio responde 502 | El proxy no llega a la web: comprueba `just ps` (¿`web` está `healthy`?) y que el proxy apunte a `127.0.0.1:3000`. |

Cada guía de `docs/` tiene su propia tabla de solución de problemas con más casos.

## Documentación

Toda la documentación está en [`docs/`](docs/README.md):
- [Arquitectura del monorepo](docs/arquitectura.md)
- [Backend `api-usuarios`: autenticación y usuarios](docs/services/api-usuarios.md)
- [Backend `api-autos`: instalación, operación y solución de problemas](docs/services/api-autos.md)
- [Frontend `web` (Nuxt 4 + Vuetify 4)](docs/apps/web.md)
- [Librería `auth-jwt`](docs/libs/auth-jwt.md)
- [Versionado y releases (release-please)](docs/releases.md): los commits siguen Conventional Commits (`feat:`, `fix:`...) y las ramas, `tipo/scope/descripcion`
