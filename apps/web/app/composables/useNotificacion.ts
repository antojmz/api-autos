/**
 * useNotificacion — Mensajes breves (snackbar) para toda la aplicación.
 * `useState` crea un estado compartido entre componentes y seguro en SSR
 * (cada petición del servidor tiene el suyo).
 */
interface Notificacion {
  visible: boolean
  texto: string
  color: 'success' | 'error' | 'info' | 'warning'
}

export function useNotificacion() {
  const notificacion = useState<Notificacion>('notificacion', () => ({
    visible: false,
    texto: '',
    color: 'info',
  }))

  function notificar(texto: string, color: Notificacion['color'] = 'success') {
    notificacion.value = { visible: true, texto, color }
  }

  return { notificacion, notificar }
}
