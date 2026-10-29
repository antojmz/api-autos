# Documentación

Toda la documentación del monorepo vive en esta carpeta.

| Documento | Contenido |
|---|---|
| [arquitectura.md](arquitectura.md) | Estructura del monorepo, convenciones y cómo añadir un servicio, una app o una librería |
| [services/api-autos.md](services/api-autos.md) | Backend `api-autos`: requisitos, levantar desde cero con Docker, migraciones, pruebas y solución de problemas |

## Organización

```
docs/
├── README.md          este índice
├── arquitectura.md    visión general del monorepo
├── services/          un documento por backend   (services/<nombre>.md)
├── apps/              un documento por frontend  (apps/<nombre>.md), cuando existan
└── libs/              un documento por librería  (libs/<nombre>.md), cuando existan
```

Cuando añadas un documento, enlázalo en la tabla de arriba.
