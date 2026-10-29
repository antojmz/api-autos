/**
 * POST /api/auth/logout — Cierra la sesión borrando la cookie.
 * (Los JWT no se pueden "anular" en el servidor: el token deja de usarse
 * porque el navegador ya no lo tiene, y además expira solo.)
 */
export default defineEventHandler((event) => {
  borrarToken(event)
  setResponseStatus(event, 204)
  return null
})
