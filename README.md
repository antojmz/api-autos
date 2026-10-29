# api-autos — Monorepo

Monorepo del proyecto Concesionario de Autos: backends, frontend y librerías compartidas en un solo repositorio.

```
.
├── services/
│   ├── api-usuarios/    Autenticación (JWT) y CRUD de usuarios
│   └── api-autos/       API REST de autos y modelos (requiere token)
├── apps/                Frontends (todavía vacío)
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
| api-usuarios | http://127.0.0.1:8001/docs | Inicia sesión con el admin del `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) |
| api-autos | http://127.0.0.1:8000/docs | Pulsa **Authorize** y pega el token obtenido en api-usuarios |

Si un puerto está ocupado: `AUTOS_PORT=8002 USUARIOS_PORT=8011 docker compose up -d`.

## Documentación

Toda la documentación está en [`docs/`](docs/README.md):
- [Arquitectura del monorepo](docs/arquitectura.md)
- [Backend `api-usuarios`: autenticación y usuarios](docs/services/api-usuarios.md)
- [Backend `api-autos`: instalación, operación y solución de problemas](docs/services/api-autos.md)
- [Librería `auth-jwt`](docs/libs/auth-jwt.md)
