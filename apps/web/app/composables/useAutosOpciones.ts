/**
 * useAutosOpciones — Lista de autos para los selectores (crear modelo,
 * filtrar modelos). La API devuelve como máximo 100 por página: suficiente
 * para esta demo; con más datos convendría un autocompletado con búsqueda.
 */
import type { Auto, Pagina } from '#shared/types/api'

export async function useAutosOpciones() {
  const requestFetch = useRequestFetch()
  const { data, refresh } = await useAsyncData('autos-opciones', () =>
    requestFetch<Pagina<Auto>>('/api/autos/autos', { query: { limit: 100 } }),
  )
  return { autos: computed(() => data.value?.items ?? []), recargarAutos: refresh }
}
