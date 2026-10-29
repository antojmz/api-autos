/**
 * GET /api/salud — Comprobación de vida para el HEALTHCHECK de Docker.
 * No consulta las APIs: solo indica que el servidor de Nuxt responde.
 */
export default defineEventHandler(() => ({ estado: 'ok' }))
