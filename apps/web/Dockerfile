# =============================================================================
# Dockerfile — Imagen del frontend (Nuxt 4 + Vuetify 4).
#
# Multi-stage:
#   1. builder: instala dependencias y compila (npm run build -> .output/).
#   2. runtime: solo copia .output/, que ya incluye el servidor y lo necesario
#      de node_modules. La imagen final no tiene código fuente ni herramientas
#      de compilación.
#
# El contexto es la RAÍZ del monorepo (igual que los backends); qué archivos
# entran lo decide Dockerfile.dockerignore.
# Construir:  docker compose build web
# =============================================================================

FROM node:24-slim AS builder
WORKDIR /app

# Primero solo package.json + lock: Docker cachea `npm ci` mientras no
# cambien las dependencias. --ignore-scripts: el "postinstall" (nuxt prepare)
# necesita el código, que aún no se ha copiado; el build lo ejecuta igualmente.
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --ignore-scripts

COPY apps/web ./
RUN npm run build

# -----------------------------------------------------------------------------
FROM node:24-slim AS runtime

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    NUXT_TELEMETRY_DISABLED=1

WORKDIR /app
COPY --from=builder --chown=node:node /app/.output ./.output

# Usuario sin privilegios (viene en la imagen oficial de Node).
USER node
EXPOSE 3000

# fetch está incluido en Node: no hace falta instalar curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/api/salud').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", ".output/server/index.mjs"]
