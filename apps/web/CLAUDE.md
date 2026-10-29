# CLAUDE.md — apps/web

Contexto para agentes que programen en el frontend. Las reglas generales del monorepo están en el `CLAUDE.md` de la raíz. La guía completa está en `docs/apps/web.md`.

## Qué es

Frontend en **Nuxt 4.6** + **Vuetify 4.3** (TypeScript, estructura `app/` de Nuxt 4). Cubre la autenticación, el CRUD de autos y modelos y la administración de usuarios. Es didáctico, como el resto del monorepo: el código va **comentado en español**.

## Arquitectura (no romper)

- **BFF**: el navegador solo llama a `/api/...` de Nuxt. `server/` hace de proxy hacia `api-usuarios` y `api-autos`.
- **El JWT nunca llega al navegador**:
  - Vive en la cookie `sesion` (`httpOnly`, `SameSite=Strict`).
  - No lo devuelvas en ninguna respuesta, no lo guardes en `useState`, `localStorage` ni `useCookie`, y no lo expongas en `runtimeConfig.public`.
- **Proxy** `server/api/[servicio]/[...ruta].ts`:
  - Lista blanca `RUTAS_PERMITIDAS` y segmentos `[A-Za-z0-9_-]`.
  - Para exponer un recurso nuevo de una API, añade su primer segmento a la lista blanca.
  - Nunca permitas `auth`, porque devolvería el token en JSON.
- **CSRF**: `server/middleware/csrf.ts` exige `application/json` en POST/PUT/PATCH/DELETE. En el cliente, usa siempre `useApi().api()`, que añade la cabecera incluso en DELETE.
- **Errores del BFF**: usa `responderError(event, status, detail)`, que tiene el mismo formato `{detail}` que las APIs. Nunca devuelvas trazas ni URLs internas.
- Las URLs de las APIs están en `runtimeConfig` **privado** (`NUXT_API_AUTOS_URL`, `NUXT_API_USUARIOS_URL`).

## Convenciones

**Datos**
- Para cargar datos en páginas (SSR) usa `useAsyncData` con `useRequestFetch()`, que reenvía la cookie en el servidor. Para tablas, usa `await usePaginado<T>(clave, url, () => filtros)` con `<v-data-table-server>` y `OPCIONES_POR_PAGINA`.
- Para las mutaciones (clic, submit) usa `useApi().api()`. Maneja 401 (envía al login) y muestra los demás errores con `useNotificacion`.
- `mensajeDeError(e)` convierte cualquier error de la API en texto.

**Sesión y permisos**
- La sesión está en `useAuth()`: `usuario`, `esAdmin`, `login`, `logout`, `registro` y `cargarSesion`.
- Los permisos de página se declaran con `definePageMeta({ publica: true })` o `definePageMeta({ soloAdmin: true })`; los tipos están en `app/types/meta.d.ts`.
- Ocultar las acciones de admin con `esAdmin` es solo UX: las APIs devuelven 403 igualmente.

**Formularios**
- Usa las reglas de `app/utils/reglas.ts`, que replican las validaciones de los backends. Si cambia una regla en un backend, actualízala aquí.
- Las contraseñas no se recortan.
- Las fechas se manejan como texto `AAAA-MM-DD`: `hoyISO()` y `formatearFecha()`, nunca `new Date(iso)`, para evitar desfases de zona horaria.
- Los precios viajan como **string** (`"25990.50"`); para mostrarlos, usa `formatearPrecio()`.

**Tipos y Vuetify**
- Los tipos de las APIs están en `shared/types/api.ts` (import `#shared/types/api`). Mantenlos alineados con los esquemas Pydantic.
- Vuetify 4 se integra con `vite-plugin-vuetify` (`autoImport`) y `app/plugins/vuetify.ts`. **No** uses `vuetify-nuxt-module`, que solo existe como RC. Los valores por defecto de los componentes van en `defaults` del plugin.

## Comandos

```bash
# Recomendado (desde la raíz): todo en Docker con recarga en caliente
just dev            # web-dev (nuxt dev) + APIs; no requiere Node local
just typecheck      # DEBE pasar sin errores

# Alternativa desde apps/web (requiere Node >= 24.15 y las APIs en Docker)
npm install
npm run dev          # http://localhost:3000
npm run typecheck    # DEBE pasar sin errores
npm run build

# Desde la raíz (Docker)
docker compose up -d --build web
```

## Verificación

1. `npm run typecheck` y `npm run build` sin errores.
2. Con `docker compose up -d --build`, debe pasar la carpeta **"3. Web (BFF)"** de la colección de la raíz (17 peticiones):
   `npx -y newman run API_Monorepo.postman_collection.json --folder "3. Web (BFF)" --env-var "adminPassword=$PW"`.
   Cubre:
   - la cookie `HttpOnly` y `SameSite=Strict`, y que el body del login no contenga `access_token`;
   - 401 sin sesión, 415 sin JSON (CSRF) y los 404 del proxy (servicio desconocido, `/auth`, traversal);
   - logout.
   Si cambias el BFF, actualiza esa carpeta.
   Además, `/autos` sin sesión debe dar 302 a `/login`.
3. Recorrer las páginas como admin y como usuario normal: este último no ve "Usuarios" ni los botones de eliminar.

## Mantenimiento

- Si cambian los endpoints de las APIs, actualiza `shared/types/api.ts`, las páginas y `docs/apps/web.md`.
- La versión de `package.json` la gestiona release-please: no la edites a mano.
