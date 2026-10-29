/**
 * useDebounced — Copia de un ref que se actualiza solo cuando el original deja
 * de cambiar durante `ms` milisegundos. Útil en buscadores: no se llama a la
 * API por cada tecla.
 */
import type { Ref } from 'vue'

export function useDebounced<T>(origen: Ref<T>, ms = 400): Ref<T> {
  const valor = ref(origen.value) as Ref<T>
  let temporizador: ReturnType<typeof setTimeout> | undefined
  watch(origen, (nuevo) => {
    clearTimeout(temporizador)
    temporizador = setTimeout(() => {
      valor.value = nuevo
    }, ms)
  })
  onScopeDispose(() => clearTimeout(temporizador))
  return valor
}
