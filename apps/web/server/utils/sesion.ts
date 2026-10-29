/**
 * server/utils/sesion.ts — Utilidades del BFF (solo se ejecutan en el servidor).
 *
 * Los archivos de server/utils/ se importan automáticamente en todas las rutas
 * de server/. Aquí se centraliza:
 *   - La cookie de sesión que guarda el JWT.
 *   - Las URLs de las APIs (configuración privada, nunca llega al navegador).
 *   - Una función para llamar a las APIs y reenviar su respuesta tal cual.
 */
import type { H3Event } from 'h3'
import type { ErrorApi } from '#shared/types/api'

export const COOKIE_SESION = 'sesion'

export type Servicio = 'autos' | 'usuarios'

/**
 * Guarda el token en una cookie:
 *  - httpOnly: JavaScript del navegador NO puede leerla. Aunque un atacante
 *    lograra inyectar código (XSS), no podría robar el token.
 *  - sameSite 'strict': el navegador no la envía en peticiones que se originan
 *    en otro sitio (protección contra CSRF).
 *  - secure: solo viaja por HTTPS (configurable para poder usar http://localhost).
 *  - maxAge: dura lo mismo que el token (expires_in).
 */
export function guardarToken(event: H3Event, token: string, segundos: number) {
  setCookie(event, COOKIE_SESION, token, {
    httpOnly: true,
    sameSite: 'strict',
    secure: useRuntimeConfig(event).cookieSecure === true,
    path: '/',
    maxAge: segundos,
  })
}

export function leerToken(event: H3Event): string | undefined {
  return getCookie(event, COOKIE_SESION)
}

export function borrarToken(event: H3Event) {
  deleteCookie(event, COOKIE_SESION, { path: '/' })
}

export function urlServicio(event: H3Event, servicio: Servicio): string {
  const config = useRuntimeConfig(event)
  return servicio === 'autos' ? config.apiAutosUrl : config.apiUsuariosUrl
}

/**
 * Responde un error con el MISMO formato {detail} que usan las APIs, para que
 * el frontend trate igual los errores del BFF y los de los backends.
 * Uso: `return responderError(event, 404, 'Recurso no encontrado')`.
 */
export function responderError(event: H3Event, statusCode: number, detail: string): ErrorApi {
  setResponseStatus(event, statusCode)
  return { detail }
}

interface OpcionesLlamada {
  method?: string
  query?: Record<string, unknown>
  body?: unknown
  headers?: Record<string, string>
}

/**
 * Llama a una API y devuelve {status, data} SIN lanzar errores por códigos
 * 4xx/5xx (ignoreResponseError), para poder reenviarlos al navegador.
 * Si la API no responde (caída, red), responde 503 con un mensaje genérico:
 * nunca se exponen URLs internas ni trazas.
 */
export async function llamarApi<T = unknown>(
  event: H3Event,
  servicio: Servicio,
  ruta: string,
  opciones: OpcionesLlamada = {},
): Promise<{ status: number; data: T }> {
  try {
    const respuesta = await $fetch.raw<T>(`${urlServicio(event, servicio)}${ruta}`, {
      method: (opciones.method ?? 'GET') as 'GET',
      query: opciones.query,
      body: opciones.body as BodyInit | Record<string, unknown> | undefined,
      headers: opciones.headers,
      ignoreResponseError: true,
      // Una API colgada no debe bloquear al BFF indefinidamente.
      timeout: 15_000,
    })
    return { status: respuesta.status, data: respuesta._data as T }
  } catch (error) {
    console.error(`[bff] ${servicio} no responde:`, (error as Error).message)
    // createError corta la petición; h3 lo convierte en una respuesta 503.
    throw createError({ statusCode: 503, statusMessage: 'Servicio no disponible' })
  }
}

/** Cabecera Authorization a partir de la cookie de sesión. */
export function cabeceraAuth(token: string): Record<string, string> {
  return { authorization: `Bearer ${token}` }
}
