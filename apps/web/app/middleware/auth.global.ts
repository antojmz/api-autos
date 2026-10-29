/**
 * middleware/auth.global.ts — Protege las páginas.
 *
 * Los middlewares de ruta con sufijo ".global" se ejecutan en CADA navegación
 * (en el servidor en la primera carga y en el navegador después).
 *   - Páginas con `definePageMeta({ publica: true })` (login, registro): si ya
 *     hay sesión, se redirige al inicio.
 *   - El resto exige sesión; si no hay, se va al login recordando la página.
 *   - `soloAdmin: true`: si el usuario no es admin, vuelve al inicio.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  const { usuario, esAdmin, cargarSesion } = useAuth()
  await cargarSesion()

  if (to.meta.publica) {
    if (usuario.value) return navigateTo('/')
    return
  }
  if (!usuario.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
  if (to.meta.soloAdmin && !esAdmin.value) {
    return navigateTo('/')
  }
})
