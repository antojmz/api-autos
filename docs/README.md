# Documentación

Toda la documentación del monorepo vive en esta carpeta.

| Documento | Contenido |
|---|---|
| [arquitectura.md](arquitectura.md) | Estructura del monorepo, autenticación entre servicios, base de datos compartida, convenciones y cómo añadir un servicio, una app o una librería |
| [services/api-usuarios.md](services/api-usuarios.md) | Backend `api-usuarios`: registro, login JWT, CRUD de usuarios, roles, soft delete, levantar desde cero y solución de problemas |
| [services/api-autos.md](services/api-autos.md) | Backend `api-autos`: requisitos, levantar desde cero con Docker, autenticación, migraciones, pruebas y solución de problemas |
| [libs/auth-jwt.md](libs/auth-jwt.md) | Librería compartida de JWT: API, configuración, decisiones y límites |

## Organización

```
docs/
├── README.md          este índice
├── arquitectura.md    visión general del monorepo
├── services/          un documento por backend   (services/<nombre>.md)
├── apps/              un documento por frontend  (apps/<nombre>.md), cuando existan
└── libs/              un documento por librería  (libs/<nombre>.md)
```

Cuando añadas un documento, enlázalo en la tabla de arriba.
