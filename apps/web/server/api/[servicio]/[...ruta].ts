/**
 * /api/[servicio]/[...ruta] — Proxy autenticado hacia las APIs.
 *
 * Ejemplos:
 *   GET    /api/autos/autos?limit=10      -> api-autos     GET    /autos?limit=10
 *   PUT    /api/autos/modelos/3           -> api-autos     PUT    /modelos/3
 *   PATCH  /api/usuarios/usuarios/me      -> api-usuarios  PATCH  /usuarios/me
 *
 * El navegador nunca envía ni conoce el token: este proxy lo toma de la
 * cookie httpOnly y lo añade como `Authorization: Bearer <token>`.
 *
 * Seguridad:
 *  - Lista blanca de servicios Y del primer segmento de la ruta. Así no se
 *    puede usar el proxy para llegar a rutas no previstas (p. ej.
 *    /api/usuarios/auth/login devolvería el token en JSON al navegador).
 *  - Cada segmento solo admite [A-Za-z0-9_-]: no hay "..", barras codificadas
 *    ni caracteres raros que permitan salir de la API (path traversal).
 *  - No se reenvían las cookies ni otras cabeceras del navegador.
 */
import type { Servicio } from '../../utils/sesion'

const RUTAS_PERMITIDAS: Record<Servicio, Set<string>> = {
  autos: new Set(['autos', 'modelo', 'modelos']),
  usuarios: new Set(['usuarios']),
}
const SEGMENTO_VALIDO = /^[A-Za-z0-9_-]+$/
const METODOS_CON_CUERPO = new Set(['POST', 'PUT', 'PATCH'])

export default defineEventHandler(async (event) => {
  const servicio = getRouterParam(event, 'servicio') as Servicio | undefined
  const ruta = getRouterParam(event, 'ruta', { decode: true }) ?? ''
  const segmentos = ruta.split('/')

  if (
    !servicio ||
    !(servicio in RUTAS_PERMITIDAS) ||
    !RUTAS_PERMITIDAS[servicio].has(segmentos[0] ?? '') ||
    !segmentos.every((s) => SEGMENTO_VALIDO.test(s))
  ) {
    return responderError(event, 404, 'Recurso no encontrado')
  }

  // Sin sesión no tiene sentido llamar a la API.
  const token = leerToken(event)
  if (!token) return responderError(event, 401, 'No autenticado')

  const respuesta = await llamarApi(event, servicio, `/${segmentos.join('/')}`, {
    method: event.method,
    query: getQuery(event),
    body: METODOS_CON_CUERPO.has(event.method) ? await readBody(event) : undefined,
    headers: cabeceraAuth(token),
  })

  // Token caducado o usuario desactivado: se cierra la sesión del navegador.
  if (respuesta.status === 401) borrarToken(event)

  // Se devuelven el código y el cuerpo de la API tal cual: ya vienen
  // saneados (sin trazas ni datos internos).
  setResponseStatus(event, respuesta.status)
  return respuesta.data ?? null
})
