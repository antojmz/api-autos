/**
 * useAuth — Estado de la sesión en el frontend.
 *
 * El token JWT NO está aquí (vive en una cookie httpOnly que solo maneja el
 * servidor de Nuxt). El frontend solo conoce el PERFIL del usuario, que usa
 * para mostrar su nombre y decidir qué opciones enseñar (p. ej. las de admin).
 * Ocultar un botón no es seguridad: las APIs igualmente responden 403.
 */
import type { Usuario } from '#shared/types/api'

export function useAuth() {
  const usuario = useState<Usuario | null>('usuario', () => null)
  const sesionCargada = useState<boolean>('sesion-cargada', () => false)
  const esAdmin = computed(() => usuario.value?.rol === 'admin')

  /**
   * Pregunta al BFF quién es el usuario de la cookie. Se ejecuta una sola vez
   * (normalmente en el servidor, durante el primer renderizado); el resultado
   * viaja al navegador dentro del HTML gracias a useState.
   * useRequestFetch: en el servidor, reenvía las cookies de la petición original.
   */
  async function cargarSesion() {
    if (sesionCargada.value) return
    try {
      usuario.value = await useRequestFetch()<Usuario>('/api/auth/sesion')
    } catch {
      usuario.value = null
    } finally {
      sesionCargada.value = true
    }
  }

  async function login(username: string, password: string) {
    usuario.value = await $fetch<Usuario>('/api/auth/login', {
      method: 'POST',
      body: { username, password },
    })
  }

  async function registro(datos: { username: string; email: string; nombre_completo: string; password: string }) {
    await $fetch('/api/auth/registro', { method: 'POST', body: datos })
  }

  /** Cierra la sesión. `redirigir=false` cuando ya se va a navegar a otra parte. */
  async function logout(redirigir = true) {
    try {
      await $fetch('/api/auth/logout', { method: 'POST', body: {} })
    } finally {
      usuario.value = null
      if (redirigir) await navigateTo('/login')
    }
  }

  return { usuario, esAdmin, cargarSesion, login, registro, logout }
}
