# Frontend `web` (`apps/web`)

Aplicación web del concesionario, hecha con **Nuxt 4** y **Vuetify 4**. Cubre:
- Inicio de sesión, registro y perfil (datos y cambio de contraseña).
- CRUD de **autos** y de sus **modelos**.
- Administración de **usuarios** (solo admin).

Todos los comandos se ejecutan **desde la raíz del monorepo**, salvo los de desarrollo local, que se ejecutan en `apps/web`.

---

## 1. Arquitectura: BFF (Backend For Frontend)

```
                     ┌──────────────── Nuxt (apps/web, :3000) ─────────────────┐
  Navegador ───────► │  páginas (SSR + Vue)          server/api  (BFF, Nitro) │
  (solo habla con    │                                 /api/auth/login ───────┼──► api-usuarios /auth/login
   Nuxt; cookie      │                                 /api/auth/sesion ──────┼──► api-usuarios /usuarios/me
   httpOnly)         │                                 /api/autos/...  ───────┼──► api-autos    /...
                     │                                 /api/usuarios/... ─────┼──► api-usuarios /...
                     └──────────────────────────────── añade Authorization ───┘
```

- El navegador **nunca** llama a las APIs directamente ni ve el token JWT.
- En el login, el servidor de Nuxt obtiene el token de `api-usuarios` y lo guarda en la cookie `sesion`:
  - `httpOnly`: JavaScript no puede leerla, así que un XSS no puede robar el token.
  - `SameSite=Strict`, con la misma duración que el token (30 minutos por defecto).
  - La respuesta del login solo incluye el **perfil** del usuario.
- El proxy `server/api/[servicio]/[...ruta].ts` toma el token de la cookie, añade `Authorization: Bearer` y reenvía la petición a la API correspondiente. Devuelve el código y el JSON de la API tal cual.
- Como el navegador solo habla con Nuxt, **no hay CORS**.
- Las URLs de las APIs son configuración privada del servidor: nunca llegan al navegador.

### Medidas de seguridad del BFF

| Medida | Dónde |
|---|---|
| Token solo en una cookie `httpOnly` + `SameSite=Strict` (+ `Secure` con HTTPS) | `server/utils/sesion.ts` |
| Login y sesión nunca devuelven el token al navegador | `server/api/auth/*.ts` |
| Lista blanca de servicios **y** del primer tramo de la ruta (`autos`, `modelo`, `modelos`, `usuarios`). El proxy no da acceso a `/auth/login` | `server/api/[servicio]/[...ruta].ts` |
| Cada tramo de la ruta solo admite `[A-Za-z0-9_-]`, lo que bloquea `..` y barras codificadas (path traversal) | proxy |
| No se reenvían al backend las cookies ni otras cabeceras del navegador | proxy |
| CSRF: las peticiones que modifican datos deben ser `application/json` (si no, 415) | `server/middleware/csrf.ts` |
| Si una API responde 401, se borra la cookie. Si una API no responde, se devuelve 503 sin detalles | `server/utils/sesion.ts`, proxy |
| La redirección tras el login solo acepta rutas internas (`/…`), lo que evita una redirección abierta | `app/pages/login.vue` |
| Cabeceras `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, y `Cache-Control: no-store` en `/api/**` | `nuxt.config.ts` (`routeRules`) |
| Ocultar los botones de admin es solo comodidad: las APIs responden **403** igualmente | páginas |

---

## 2. Páginas

| Ruta | Acceso | Qué hace |
|---|---|---|
| `/login`, `/registro` | público (con sesión redirige a `/`) | Iniciar sesión (username o email) / crear cuenta e iniciar sesión |
| `/` | autenticado | Totales de autos, modelos y usuarios (estos solo para admin) |
| `/autos` | autenticado | Tabla paginada en el servidor, búsqueda por marca, crear/editar. **Eliminar solo admin** (borra también sus modelos) |
| `/autos/[id]` | autenticado | Detalle del auto, editarlo y CRUD de sus modelos |
| `/modelos` | autenticado | Todos los modelos, filtro por auto, crear/editar. **Eliminar solo admin** |
| `/usuarios` | **solo admin** | Búsqueda (`q`), filtros de rol y estado, crear, editar (datos, rol, activo, contraseña) y eliminar (soft delete) |
| `/perfil` | autenticado | Editar mis datos y cambiar mi contraseña |

- El middleware `app/middleware/auth.global.ts` protege todas las páginas, salvo las marcadas con `definePageMeta({ publica: true })`.
- Sin sesión, redirige a `/login?redirect=<página>`.
- Las páginas con `soloAdmin: true` redirigen al inicio a quien no sea admin.

Los formularios validan con las **mismas reglas que los backends** (`app/utils/reglas.ts`): marca y nombre seguros, año de 1886 al año siguiente, precio con 2 decimales, fechas no futuras, username, email y contraseña de 10 caracteres o más con letra y número. La validación definitiva la hacen siempre las APIs, y sus errores 422 se muestran al usuario.

---

## 3. Ejecutar con Docker (recomendado)

```bash
docker compose build web
docker compose up -d          # levanta api-usuarios, api-autos y web
```

- La web queda en **http://127.0.0.1:3000**. Inicia sesión con el admin de `services/api-usuarios/.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) o crea una cuenta.
- El servicio `web` espera a que las dos APIs estén `healthy` (`depends_on`).
- Dentro de Docker, el BFF llama a las APIs por la red interna (`http://api-autos:8000` y `http://api-usuarios:8000`), así que **los puertos del host de las APIs no afectan a la web**.
- Si el puerto 3000 está ocupado: `WEB_PORT=3001 docker compose up -d`.

La imagen (`apps/web/Dockerfile`):
- Se construye en dos etapas con `node:24-slim`.
- La imagen final solo contiene `.output/` y corre como el usuario `node`.
- Incluye un `HEALTHCHECK` contra `/api/salud`.
- El contexto de construcción es la raíz; `apps/web/Dockerfile.dockerignore` deja entrar solo `apps/web`, sin `node_modules`, `.nuxt`, `.output` ni `.env`.

---

## 4. Desarrollo (recarga en caliente)

**Recomendado: `just dev`** (desde la raíz). Levanta las APIs y el frontend en el contenedor `web-dev`:
- `nuxt dev` monta `apps/web` y recarga al guardar (HMR).
- No necesitas Node instalado.
- Las dependencias de Linux van en un volumen propio (`web_node_modules`).
- Si añades un paquete a `package.json`, reinicia `just dev`.
- `just typecheck` comprueba los tipos dentro del contenedor.

**Alternativa sin Docker para el frontend**: requiere **Node.js 24.15 o superior** (lo exige Nuxt 4.6) y las APIs levantadas con Docker.

```bash
docker compose up -d api-usuarios api-autos     # desde la raíz
cd apps/web
cp .env.example .env        # solo si las APIs no están en :8000 / :8001
npm install
npm run dev                 # http://localhost:3000
```

Si el puerto 3000 lo usa el contenedor `web`, detenlo (`docker compose stop web`) o usa `npm run dev -- --port 3001`.

| Script | Para qué |
|---|---|
| `npm run dev` | Servidor de desarrollo con recarga en caliente |
| `npm run typecheck` | Comprobación de tipos (TypeScript + plantillas Vue) |
| `npm run build` | Build de producción en `.output/` |
| `npm run preview` | Ejecuta el build de producción en local |

### Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `NUXT_API_AUTOS_URL` | `http://127.0.0.1:8000` | URL de `api-autos` (privada, solo la usa el servidor) |
| `NUXT_API_USUARIOS_URL` | `http://127.0.0.1:8001` | URL de `api-usuarios` (privada) |
| `NUXT_COOKIE_SECURE` | `false` | Pon `true` con HTTPS. Con `true` en `http://`, el navegador no guarda la cookie y no se puede iniciar sesión |

En Docker, Compose define estas variables (`WEB_COOKIE_SECURE` en el `.env` de la raíz controla la última).

---

## 5. Estructura

```
apps/web/
├── nuxt.config.ts            Vuetify (vite-plugin-vuetify), runtimeConfig privado, cabeceras
├── shared/types/api.ts       tipos de las APIs (Auto, Modelo, Usuario, Pagina<T>, ErrorApi)
├── server/                   BFF (solo servidor)
│   ├── utils/sesion.ts       cookie, URLs, llamarApi, responderError
│   ├── middleware/csrf.ts    exige JSON en métodos que modifican
│   └── api/                  auth/{login,registro,logout,sesion}, salud, [servicio]/[...ruta] (proxy)
└── app/
    ├── plugins/vuetify.ts    createVuetify: tema claro/oscuro (cookie "tema"), locale es
    ├── composables/          useAuth, useApi (errores), usePaginado (tablas), useAutosOpciones, useNotificacion, useDebounced
    ├── middleware/auth.global.ts
    ├── utils/                reglas.ts (validación), formato.ts (fechas, precios)
    ├── components/           AutoFormulario, ModeloFormulario, UsuarioFormulario, ConfirmarDialogo
    ├── layouts/              default (menú + barra), auth (login/registro)
    └── pages/                index, login, registro, perfil, autos/, modelos/, usuarios/
```

---

## 6. Probar el BFF con Postman

La colección única de la raíz, `API_Monorepo.postman_collection.json`, tiene la carpeta **"3. Web (BFF)"**, con 17 peticiones. Postman guarda la cookie `sesion` en su *cookie jar*, igual que un navegador. Las pruebas cubren:
- **Login**: comprueban que la cookie es `HttpOnly` y `SameSite=Strict` y que el token no aparece en el cuerpo.
- **Proxy** hacia las dos APIs.
- **Seguridad**: 401 sin sesión, 415 sin JSON (CSRF) y 404 en servicios desconocidos, rutas `/auth` y path traversal.
- **Logout**.

```bash
PW=$(grep ADMIN_PASSWORD services/api-usuarios/.env | cut -d= -f2-)
npx -y newman run API_Monorepo.postman_collection.json --folder "3. Web (BFF)" --env-var "adminPassword=$PW"
```

## 7. Solución de problemas

| Síntoma | Solución |
|---|---|
| El login "funciona" pero vuelve siempre a `/login` | `NUXT_COOKIE_SECURE=true` sin HTTPS: el navegador descarta la cookie. Ponlo en `false` en local. |
| Errores 503 "Servicio no disponible" | El BFF no llega a las APIs. En Docker: `docker compose ps` (¿están `healthy`?). En local: revisa `NUXT_API_*_URL`. |
| 415 en peticiones desde otra herramienta (curl, Postman) | El BFF exige `Content-Type: application/json` en POST/PUT/PATCH/DELETE. |
| Tras unos 30 minutos te envía al login | El token expiró (`JWT_MINUTOS_EXPIRACION`). Es el comportamiento esperado: no hay refresh tokens. |
| Un usuario desactivado sigue viendo autos un rato | `api-autos` valida el token sin consultar usuarios (ver `docs/libs/auth-jwt.md`). En `/usuarios` y el perfil pierde acceso al instante. |
| `npm install` avisa de `engines` | Actualiza Node a 24.15 o superior (`nvm install 24`). |
| Los selectores de autos muestran como máximo 100 | Es el límite de página de la API. Basta para la demo; con más datos convendría un autocompletado con búsqueda. |
