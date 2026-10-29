<!-- pages/modelos/index.vue — Todos los modelos, con filtro por auto y CRUD. -->
<script setup lang="ts">
import type { Modelo } from '#shared/types/api'

useHead({ title: 'Modelos' })
const { esAdmin } = useAuth()
const { api } = useApi()
const { notificar } = useNotificacion()

const { autos } = await useAutosOpciones()
const autoFiltro = ref<number | null>(null)
const lista = await usePaginado<Modelo>('modelos', '/api/autos/modelos', () => ({ auto_id: autoFiltro.value }))

// Para mostrar la marca del auto en cada fila sin pedirla una a una.
const marcaPorId = computed(() => new Map(autos.value.map((a) => [a.id, a.marca])))
const opcionesAutos = computed(() => autos.value.map((a) => ({ title: `#${a.id} · ${a.marca}`, value: a.id })))

const encabezados = [
  { title: 'ID', key: 'id', width: 80 },
  { title: 'Auto', key: 'auto_id' },
  { title: 'Nombre', key: 'nombre' },
  { title: 'Año', key: 'anio' },
  { title: 'Precio', key: 'precio', align: 'end' as const },
  { title: 'Fecha de ingreso', key: 'fecha_ingreso' },
  { title: 'Acciones', key: 'acciones', align: 'end' as const, sortable: false },
]

const formularioAbierto = ref(false)
const modeloEditando = ref<Modelo | null>(null)
const confirmarAbierto = ref(false)
const modeloBorrando = ref<Modelo | null>(null)
const borrando = ref(false)

function nuevo() {
  modeloEditando.value = null
  formularioAbierto.value = true
}
function editar(m: Modelo) {
  modeloEditando.value = m
  formularioAbierto.value = true
}
function pedirBorrado(m: Modelo) {
  modeloBorrando.value = m
  confirmarAbierto.value = true
}
async function borrar() {
  if (!modeloBorrando.value) return
  borrando.value = true
  try {
    await api(`/api/autos/modelos/${modeloBorrando.value.id}`, { method: 'DELETE' })
    notificar('Modelo eliminado')
    confirmarAbierto.value = false
    await lista.recargar()
  } catch {
    // useApi ya mostró el error.
  } finally {
    borrando.value = false
  }
}
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center ga-4 mb-4">
      <h1 class="text-h4">Modelos</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" :disabled="autos.length === 0" @click="nuevo">Nuevo modelo</v-btn>
    </div>

    <v-alert v-if="autos.length === 0" type="info" variant="tonal" class="mb-4">
      Primero crea un auto en <NuxtLink to="/autos">Autos</NuxtLink>.
    </v-alert>

    <v-card>
      <v-card-text>
        <v-select
          v-model="autoFiltro"
          :items="opcionesAutos"
          label="Filtrar por auto"
          prepend-inner-icon="mdi-filter"
          clearable
          hide-details
        />
      </v-card-text>

      <v-alert v-if="lista.error.value" type="error" variant="tonal" class="mx-4" :text="mensajeDeError(lista.error.value)" />

      <v-data-table-server
        v-model:page="lista.pagina.value"
        v-model:items-per-page="lista.porPagina.value"
        :headers="encabezados"
        :items="lista.items.value"
        :items-length="lista.total.value"
        :loading="lista.cargando.value"
        :items-per-page-options="OPCIONES_POR_PAGINA"
        no-data-text="No hay modelos"
      >
        <template #[`item.auto_id`]="{ item }">
          <NuxtLink :to="`/autos/${item.auto_id}`">{{ marcaPorId.get(item.auto_id) ?? `#${item.auto_id}` }}</NuxtLink>
        </template>
        <template #[`item.precio`]="{ item }">{{ formatearPrecio(item.precio) }}</template>
        <template #[`item.fecha_ingreso`]="{ item }">{{ formatearFecha(item.fecha_ingreso) }}</template>
        <template #[`item.acciones`]="{ item }">
          <v-btn icon="mdi-pencil" variant="text" size="small" aria-label="Editar" @click="editar(item)" />
          <v-btn
            v-if="esAdmin"
            icon="mdi-delete"
            variant="text"
            size="small"
            color="error"
            aria-label="Eliminar"
            @click="pedirBorrado(item)"
          />
        </template>
      </v-data-table-server>
    </v-card>

    <ModeloFormulario
      v-model="formularioAbierto"
      :modelo="modeloEditando"
      :auto-id="modeloEditando ? null : autoFiltro"
      :autos="autos"
      @guardado="lista.recargar()"
    />
    <ConfirmarDialogo
      v-model="confirmarAbierto"
      titulo="Eliminar modelo"
      :texto="`Se eliminará el modelo «${modeloBorrando?.nombre}».`"
      :cargando="borrando"
      @confirmar="borrar"
    />
  </div>
</template>
