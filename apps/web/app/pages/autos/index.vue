<!--
  pages/autos/index.vue — Listado de autos con paginación en el servidor,
  filtro por marca y alta/edición/borrado. Borrar es solo para admin.
-->
<script setup lang="ts">
import type { Auto } from '#shared/types/api'

useHead({ title: 'Autos' })
const { esAdmin } = useAuth()
const { api } = useApi()
const { notificar } = useNotificacion()

// El filtro se aplica 400 ms después de dejar de escribir (evita una
// petición por cada tecla).
const textoMarca = ref('')
const marca = useDebounced(textoMarca, 400)

const lista = await usePaginado<Auto>('autos', '/api/autos/autos', () => ({ marca: (marca.value ?? '').trim() }))

const encabezados = [
  { title: 'ID', key: 'id', width: 80 },
  { title: 'Marca', key: 'marca' },
  { title: 'Fecha de ingreso', key: 'fecha_ingreso' },
  { title: 'Acciones', key: 'acciones', align: 'end' as const, sortable: false },
]

// Diálogos
const formularioAbierto = ref(false)
const autoEditando = ref<Auto | null>(null)
const confirmarAbierto = ref(false)
const autoBorrando = ref<Auto | null>(null)
const borrando = ref(false)

function nuevo() {
  autoEditando.value = null
  formularioAbierto.value = true
}
function editar(auto: Auto) {
  autoEditando.value = auto
  formularioAbierto.value = true
}
function pedirBorrado(auto: Auto) {
  autoBorrando.value = auto
  confirmarAbierto.value = true
}
async function borrar() {
  if (!autoBorrando.value) return
  borrando.value = true
  try {
    await api(`/api/autos/autos/${autoBorrando.value.id}`, { method: 'DELETE' })
    notificar('Auto eliminado')
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
      <h1 class="text-h4">Autos</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="nuevo">Nuevo auto</v-btn>
    </div>

    <v-card>
      <v-card-text>
        <v-text-field
          v-model="textoMarca"
          label="Buscar por marca"
          prepend-inner-icon="mdi-magnify"
          clearable
          hide-details
          maxlength="50"
          @click:clear="textoMarca = ''"
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
        no-data-text="No hay autos"
      >
        <template #[`item.marca`]="{ item }">
          <NuxtLink :to="`/autos/${item.id}`" class="font-weight-medium">{{ item.marca }}</NuxtLink>
        </template>
        <template #[`item.fecha_ingreso`]="{ item }">{{ formatearFecha(item.fecha_ingreso) }}</template>
        <template #[`item.acciones`]="{ item }">
          <v-btn icon="mdi-eye" variant="text" size="small" :to="`/autos/${item.id}`" aria-label="Ver" />
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

    <AutoFormulario v-model="formularioAbierto" :auto="autoEditando" @guardado="lista.recargar()" />
    <ConfirmarDialogo
      v-model="confirmarAbierto"
      titulo="Eliminar auto"
      :texto="`Se eliminará «${autoBorrando?.marca}» y TODOS sus modelos. Esta acción no se puede deshacer.`"
      :cargando="borrando"
      @confirmar="borrar"
    />
  </div>
</template>
