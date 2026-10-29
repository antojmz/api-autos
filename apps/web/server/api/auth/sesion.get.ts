/**
 * GET /api/auth/sesion — Usuario de la sesión actual (o 401).
 * El frontend lo llama al cargar la aplicación para saber si hay sesión.
 * Consulta api-usuarios /usuarios/me, que además comprueba en la BD que el
 * usuario siga activo.
 */
import type { Usuario } from '#shared/types/api'

export default defineEventHandler(async (event) => {
  const token = leerToken(event)
  if (!token) return responderError(event, 401, 'No autenticado')

  const respuesta = await llamarApi<Usuario>(event, 'usuarios', '/usuarios/me', {
    headers: cabeceraAuth(token),
  })
  if (respuesta.status !== 200) {
    // Token caducado, usuario desactivado o eliminado: se limpia la cookie.
    borrarToken(event)
    return responderError(event, 401, 'No autenticado')
  }
  return respuesta.data
})
