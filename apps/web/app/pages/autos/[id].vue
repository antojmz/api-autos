<!--
  pages/autos/[id].vue — Detalle de un auto y CRUD de sus modelos.
  El nombre de archivo "[id]" crea una ruta dinámica: /autos/1, /autos/2...
-->
<script setup lang="ts">
import type { Auto, Modelo } from '#shared/types/api'

const route = useRoute()
const id = Number(route.params.id)
const { esAdmin } = useAuth()
const { api } = useApi()
const { notificar } = useNotificacion()
const requestFetch = useRequestFetch()

const { data: auto, error, refresh: recargarAuto } = await useAsyncData(`auto-${id}`, () =>
  requestFetch<Auto>(`/api/autos/autos/${id}`),
)
useHead({ title: () => auto.value?.marca ?? 'Auto' })

const modelos = await usePaginado<Modelo>(`modelos-auto-${id}`, '/api/autos/modelos', () => ({ auto_id: id }))
// El formulario de modelos necesita la lista de autos; aquí solo este.
const autosFormulario = computed(() => (auto.value ? [auto.value] : []))

const encabezados = [
  { title: 'ID', key: 'id', width: 80 },
  { title: 'Nombre', key: 'nombre' },
  { title: 'Año', key: 'anio' },
  { title: 'Precio', key: 'precio', align: 'end' as const },
  { title: 'Fecha de ingreso', key: 'fecha_ingreso' },
  { title: 'Acciones', key: 'acciones', align: 'end' as const, sortable: false },
]

const autoFormularioAbierto = ref(false)
const modeloFormularioAbierto = ref(false)
const modeloEditando = ref<Modelo | null>(null)
const confirmarAbierto = ref(false)
const modeloBorrando = ref<Modelo | null>(null)
const borrando = ref(false)

function nuevoModelo() {
  modeloEditando.value = null
  modeloFormularioAbierto.value = true
}
function editarModelo(m: Modelo) {
  modeloEditando.value = m
  modeloFormularioAbierto.value = true
}
function pedirBorrado(m: Modelo) {
  modeloBorrando.value = m
  confirmarAbierto.value = true
}
async function borrarModelo() {
  if (!modeloBorrando.value) return
  borrando.value = true
  try {
    await api(`/api/autos/modelos/${modeloBorrando.value.id}`, { method: 'DELETE' })
    notificar('Modelo eliminado')
    confirmarAbierto.value = false
    await modelos.recargar()
  } catch {
    // useApi ya mostró el error.
  } finally {
    borrando.value = false
  }
}
</script>

<template>
  <div>
    <v-btn to="/autos" variant="text" prepend-icon="mdi-arrow-left" class="mb-2">Autos</v-btn>

    <v-alert v-if="error" type="error" variant="tonal" :text="mensajeDeError(error)" />

    <template v-else-if="auto">
      <v-card class="mb-6">
        <v-card-item>
          <template #prepend><v-icon icon="mdi-car" size="40" color="primary" /></template>
          <v-card-title class="text-h5">{{ auto.marca }}</v-card-title>
          <v-card-subtitle>ID {{ auto.id }} · Ingreso: {{ formatearFecha(auto.fecha_ingreso) }}</v-card-subtitle>
          <template #append>
            <v-btn prepend-icon="mdi-pencil" variant="tonal" @click="autoFormularioAbierto = true">Editar</v-btn>
          </template>
        </v-card-item>
      </v-card>

      <div class="d-flex align-center mb-4">
        <h2 class="text-h5">Modelos</h2>
        <v-spacer />
        <v-btn color="primary" prepend-icon="mdi-plus" @click="nuevoModelo">Nuevo modelo</v-btn>
      </div>

      <v-card>
        <v-data-table-server
          v-model:page="modelos.pagina.value"
          v-model:items-per-page="modelos.porPagina.value"
          :headers="encabezados"
          :items="modelos.items.value"
          :items-length="modelos.total.value"
          :loading="modelos.cargando.value"
          :items-per-page-options="OPCIONES_POR_PAGINA"
          no-data-text="Este auto aún no tiene modelos"
        >
          <template #[`item.precio`]="{ item }">{{ formatearPrecio(item.precio) }}</template>
          <template #[`item.fecha_ingreso`]="{ item }">{{ formatearFecha(item.fecha_ingreso) }}</template>
          <template #[`item.acciones`]="{ item }">
            <v-btn icon="mdi-pencil" variant="text" size="small" aria-label="Editar" @click="editarModelo(item)" />
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

      <AutoFormulario v-model="autoFormularioAbierto" :auto="auto" @guardado="recargarAuto()" />
      <ModeloFormulario
        v-model="modeloFormularioAbierto"
        :modelo="modeloEditando"
        :auto-id="auto.id"
        fijar-auto
        :autos="autosFormulario"
        @guardado="modelos.recargar()"
      />
      <ConfirmarDialogo
        v-model="confirmarAbierto"
        titulo="Eliminar modelo"
        :texto="`Se eliminará el modelo «${modeloBorrando?.nombre}».`"
        :cargando="borrando"
        @confirmar="borrarModelo"
      />
    </template>
  </div>
</template>
