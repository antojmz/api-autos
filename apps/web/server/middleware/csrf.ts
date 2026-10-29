/**
 * server/middleware/csrf.ts — Protección adicional contra CSRF.
 *
 * Los middlewares de server/middleware/ se ejecutan en TODAS las peticiones
 * que llegan al servidor de Nuxt, antes de las rutas.
 *
 * La cookie de sesión ya es SameSite=Strict. Además, toda petición a /api que
 * modifique datos debe enviar `Content-Type: application/json`: un formulario
 * HTML de otro sitio no puede enviar ese tipo de contenido (el navegador
 * exigiría una petición previa CORS, que este servidor no autoriza).
 */
const METODOS_SEGUROS = new Set(['GET', 'HEAD', 'OPTIONS'])

export default defineEventHandler((event) => {
  if (!event.path.startsWith('/api/') || METODOS_SEGUROS.has(event.method)) return

  const tipo = getRequestHeader(event, 'content-type') ?? ''
  if (!tipo.toLowerCase().startsWith('application/json')) {
    // Devolver un valor desde un middleware termina la petición aquí.
    return responderError(event, 415, 'Las peticiones deben enviarse como application/json')
  }
})
