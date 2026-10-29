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

## Arranque rápido

Requisitos: Docker Desktop y PostgreSQL corriendo en tu máquina, con una base de datos `autos`.

```bash
# 1. Configuración (ajusta las claves en cada .env)
cp .env.example .env                                         # JWT_SECRET_KEY compartida
python3 -c "import secrets; print(secrets.token_urlsafe(48))"  # genera la clave
cp services/api-usuarios/.env.example services/api-usuarios/.env   # BD + admin inicial
cp services/api-autos/.env.example services/api-autos/.env         # BD

# 2. Construir y levantar
docker compose build
docker compose up -d
```

| Servicio | URL | |
|---|---|---|
| **web** | **http://127.0.0.1:3000** | La aplicación: inicia sesión con el admin del `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) o crea una cuenta |
| api-usuarios | http://127.0.0.1:8001/docs | Inicia sesión con el admin del `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) |
| api-autos | http://127.0.0.1:8000/docs | Pulsa **Authorize** y pega el token obtenido en api-usuarios |

Si un puerto está ocupado: `AUTOS_PORT=8002 USUARIOS_PORT=8011 WEB_PORT=3001 docker compose up -d`.

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
