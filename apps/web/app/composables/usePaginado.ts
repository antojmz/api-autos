/**
 * usePaginado — Carga un listado paginado de las APIs ({total, skip, limit, items})
 * para usarlo con <v-data-table-server>.
 *
 *   const lista = await usePaginado<Auto>('autos', '/api/autos/autos', () => ({ marca: filtro.value }))
 *
 * - Se ejecuta primero en el SERVIDOR (SSR): la página llega con los datos.
 *   useRequestFetch reenvía la cookie de sesión en esa llamada.
 * - Vuelve a cargar al cambiar de página, de tamaño o de filtros.
 * - Si la sesión expiró (401), envía al login.
 */
import type { Pagina } from '#shared/types/api'

/** Quita filtros vacíos para no enviar "?marca=" a la API. */
function limpiar(filtros: Record<string, unknown>) {
  return Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== '' && v !== null && v !== undefined))
}

export async function usePaginado<T>(clave: string, url: string, filtros: () => Record<string, unknown> = () => ({})) {
  // Todos los composables se llaman ANTES del primer `await` (requisito de Nuxt).
  const pagina = ref(1)
  const porPagina = ref(10)
  const requestFetch = useRequestFetch()
  const { usuario } = useAuth()
  const claveFiltros = computed(() => JSON.stringify(limpiar(filtros())))

  // Al cambiar un filtro se vuelve a la primera página.
  watch(claveFiltros, () => {
    pagina.value = 1
  })

  const resultado = useAsyncData(
    clave,
    () =>
      requestFetch<Pagina<T>>(url, {
        query: {
          ...limpiar(filtros()),
          skip: (pagina.value - 1) * porPagina.value,
          limit: porPagina.value,
        },
      }),
    { watch: [pagina, porPagina, claveFiltros] },
  )

  async function revisarSesion(error: { statusCode?: number } | null | undefined) {
    if (error?.statusCode === 401) {
      usuario.value = null
      await navigateTo('/login')
    }
  }
  watch(resultado.error, revisarSesion)

  await resultado
  await revisarSesion(resultado.error.value)

  return {
    pagina,
    porPagina,
    items: computed(() => resultado.data.value?.items ?? []),
    total: computed(() => resultado.data.value?.total ?? 0),
    cargando: computed(() => resultado.status.value === 'pending'),
    error: resultado.error,
    recargar: resultado.refresh,
  }
}

/** Opciones de "elementos por página" (la API admite hasta 100). */
export const OPCIONES_POR_PAGINA = [
  { value: 10, title: '10' },
  { value: 25, title: '25' },
  { value: 50, title: '50' },
  { value: 100, title: '100' },
]
