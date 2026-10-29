# api-autos — Monorepo

Monorepo del proyecto Concesionario de Autos: backend, frontend y librerías compartidas en un solo repositorio.

```
.
├── services/      Backends
│   └── api-autos/     API REST de autos y modelos (FastAPI + PostgreSQL)
├── apps/          Frontends (todavía vacío)
├── libs/          Librerías compartidas (todavía vacío)
├── docs/          Toda la documentación
└── docker-compose.yml   levanta los servicios del monorepo
```

## Arranque rápido

Requisitos: Docker Desktop y PostgreSQL corriendo en tu máquina, con una base de datos `autos`.

```bash
cp services/api-autos/.env.example services/api-autos/.env   # y ajusta la clave
docker compose build
docker compose up -d
```

La API queda en http://127.0.0.1:8000/docs. Si el puerto 8000 está ocupado, usa `API_PORT=8001 docker compose up -d`.

## Documentación

Toda la documentación está en [`docs/`](docs/README.md):
- [Arquitectura del monorepo](docs/arquitectura.md)
- [Backend `api-autos`: instalación, operación y solución de problemas](docs/services/api-autos.md)
