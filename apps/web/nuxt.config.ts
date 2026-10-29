/**
 * nuxt.config.ts — Configuración del frontend (Nuxt 4 + Vuetify 4).
 *
 * Arquitectura "BFF" (Backend For Frontend):
 *   navegador ──► Nuxt (este proyecto) ──► api-usuarios / api-autos
 * El navegador SOLO habla con Nuxt. Las rutas de server/api/ hacen de proxy
 * hacia las APIs y guardan el token JWT en una cookie httpOnly que JavaScript
 * no puede leer. Ver docs/apps/web.md.
 */
import vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-01',
  devtools: { enabled: false },
  telemetry: false,

  // Vuetify se integra "a mano" (método oficial de la documentación de
  // Vuetify): el plugin de Vite importa automáticamente solo los componentes
  // que se usan (tree-shaking). El módulo vuetify-nuxt-module no se usa
  // porque aún no tiene versión estable.
  build: { transpile: ['vuetify'] },
  modules: [
    (_opciones, nuxt) => {
      nuxt.hooks.hook('vite:extendConfig', (config) => {
        // Nuxt siempre entrega `plugins` inicializado en la config de Vite.
        config.plugins!.push(vuetify({ autoImport: true }))
      })
    },
  ],
  vite: {
    vue: { template: { transformAssetUrls } },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'es' },
      title: 'Concesionario',
      meta: [{ name: 'description', content: 'Gestión de autos, modelos y usuarios' }],
    },
  },

  // runtimeConfig: configuración que se puede cambiar con variables de
  // entorno al ARRANCAR (NUXT_API_AUTOS_URL, etc.), sin reconstruir.
  // Todo lo que está fuera de `public` es PRIVADO: solo existe en el servidor
  // y nunca se envía al navegador.
  runtimeConfig: {
    apiAutosUrl: 'http://127.0.0.1:8000',
    apiUsuariosUrl: 'http://127.0.0.1:8001',
    cookieSecure: false,
  },

  // Cabeceras HTTP de seguridad (mismo criterio que las APIs).
  routeRules: {
    '/**': {
      headers: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
      },
    },
    // Las respuestas del BFF contienen datos personales: sin caché.
    '/api/**': { headers: { 'Cache-Control': 'no-store' } },
  },

  typescript: { strict: true },
})
