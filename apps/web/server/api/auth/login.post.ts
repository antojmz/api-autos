/**
 * POST /api/auth/login — Inicia sesión.
 *
 * 1. Recibe {username, password} en JSON desde el navegador.
 * 2. Llama a api-usuarios /auth/login con el FORMULARIO OAuth2 que esa API espera.
 * 3. Guarda el JWT en la cookie httpOnly y devuelve SOLO el perfil del usuario.
 *    El token nunca aparece en la respuesta: el JavaScript del navegador no lo ve.
 */
import type { ErrorApi, Usuario } from '#shared/types/api'

interface RespuestaToken {
  access_token: string
  token_type: string
  expires_in: number
}

export default defineEventHandler(async (event) => {
  const cuerpo = await readBody<{ username?: unknown; password?: unknown }>(event)

  // Validación mínima de forma; las reglas reales las aplica api-usuarios.
  if (typeof cuerpo?.username !== 'string' || typeof cuerpo?.password !== 'string') {
    setResponseStatus(event, 422)
    return {
      detail: 'Datos de entrada inválidos',
      errores: [{ campo: 'body', mensaje: 'username y password son obligatorios' }],
    } satisfies ErrorApi
  }

  const login = await llamarApi<RespuestaToken | ErrorApi>(event, 'usuarios', '/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: cuerpo.username, password: cuerpo.password }),
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
  })
  if (login.status !== 200) {
    // Se reenvía el error de la API (p. ej. 401 "Credenciales incorrectas").
    setResponseStatus(event, login.status)
    return login.data
  }

  const { access_token, expires_in } = login.data as RespuestaToken
  guardarToken(event, access_token, expires_in)

  const perfil = await llamarApi<Usuario>(event, 'usuarios', '/usuarios/me', {
    headers: cabeceraAuth(access_token),
  })
  return perfil.data
})
