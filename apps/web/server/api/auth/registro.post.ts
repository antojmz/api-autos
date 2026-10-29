/**
 * POST /api/auth/registro — Crea una cuenta (público).
 * Reenvía el JSON a api-usuarios /auth/registro, que valida todo y nunca
 * permite elegir el rol. No inicia sesión: el navegador llama luego a /login.
 */
export default defineEventHandler(async (event) => {
  const respuesta = await llamarApi(event, 'usuarios', '/auth/registro', {
    method: 'POST',
    body: await readBody(event),
  })
  setResponseStatus(event, respuesta.status)
  return respuesta.data
})
