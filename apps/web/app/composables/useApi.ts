/**
 * useApi — Llamadas a las APIs a través del BFF, con manejo de errores común.
 *
 *   const { api } = useApi()
 *   await api('/api/autos/autos', { method: 'POST', body: { marca: 'Kia' } })
 *
 * Traduce los errores a mensajes para el usuario:
 *   401 -> la sesión expiró: se limpia y se envía al login.
 *   403 -> sin permisos.  404/409 -> el `detail` de la API.
 *   422 -> la lista `errores` de validación (o el `detail`).
 */
import type { ErrorApi } from '#shared/types/api'

interface ErrorFetch {
  status?: number
  statusCode?: number
  data?: Partial<ErrorApi>
}

/** Convierte un error de $fetch en un texto legible. */
export function mensajeDeError(error: unknown): string {
  const e = error as ErrorFetch
  const estado = e?.status ?? e?.statusCode
  const datos = e?.data
  if (datos?.errores?.length) return datos.errores.map((x) => x.mensaje).join(' · ')
  if (datos?.detail) return datos.detail
  if (estado === 403) return 'No tienes permisos para esta operación'
  if (estado === 503) return 'Servicio no disponible. Intenta más tarde.'
  return 'Ocurrió un error inesperado'
}

/** Opciones de $fetch (method, body, query...). */
type OpcionesFetch = Parameters<typeof $fetch>[1]

export function useApi() {
  const { notificar } = useNotificacion()
  const { usuario } = useAuth()

  async function api<T>(url: string, opciones: OpcionesFetch = {}): Promise<T> {
    // El BFF exige `Content-Type: application/json` en toda petición que
    // modifica datos (protección CSRF, ver server/middleware/csrf.ts). $fetch
    // solo lo pone si hay cuerpo, así que se añade también para DELETE.
    const metodo = (opciones?.method ?? 'GET').toUpperCase()
    const cabeceras = metodo === 'GET' ? opciones?.headers : { 'Content-Type': 'application/json', ...opciones?.headers }
    try {
      return (await $fetch(url, { ...opciones, headers: cabeceras })) as T
    } catch (error) {
      const estado = (error as ErrorFetch)?.status ?? (error as ErrorFetch)?.statusCode
      if (estado === 401) {
        usuario.value = null
        notificar('Tu sesión expiró. Inicia sesión de nuevo.', 'warning')
        await navigateTo({ path: '/login', query: { redirect: useRoute().fullPath } })
      } else {
        notificar(mensajeDeError(error), 'error')
      }
      throw error
    }
  }

  return { api }
}
