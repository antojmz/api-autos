<!--
  pages/usuarios/index.vue — Administración de usuarios (SOLO ADMIN).
  `soloAdmin: true` hace que el middleware redirija a quien no sea admin; aun
  así, api-usuarios responde 403 si alguien llama a la API directamente.
  Eliminar es un "soft delete": la cuenta queda desactivada y su username y
  email siguen reservados.
-->
<script setup lang="ts">
import type { Rol, Usuario } from '#shared/types/api'

definePageMeta({ soloAdmin: true })
useHead({ title: 'Usuarios' })

const { usuario: yo } = useAuth()
const { api } = useApi()
const { notificar } = useNotificacion()

const textoBusqueda = ref('')
const busqueda = useDebounced(textoBusqueda, 400)
const rolFiltro = ref<Rol | null>(null)
const estadoFiltro = ref<boolean | null>(null)

const lista = await usePaginado<Usuario>('usuarios', '/api/usuarios/usuarios', () => ({
  q: (busqueda.value ?? '').trim(),
  rol: rolFiltro.value,
  activo: estadoFiltro.value,
}))

const opcionesRol = [
  { title: 'Administrador', value: 'admin' },
  { title: 'Usuario', value: 'usuario' },
]
const opcionesEstado = [
  { title: 'Activos', value: true },
  { title: 'Desactivados / eliminados', value: false },
]
const encabezados = [
  { title: 'ID', key: 'id', width: 70 },
  { title: 'Username', key: 'username' },
  { title: 'Nombre', key: 'nombre_completo' },
  { title: 'Email', key: 'email' },
  { title: 'Rol', key: 'rol' },
  { title: 'Estado', key: 'activo' },
  { title: 'Acciones', key: 'acciones', align: 'end' as const, sortable: false },
]

function estado(u: Usuario) {
  if (u.eliminado_en) return { texto: 'Eliminado', color: 'error' }
  return u.activo ? { texto: 'Activo', color: 'success' } : { texto: 'Desactivado', color: 'warning' }
}

const formularioAbierto = ref(false)
const usuarioEditando = ref<Usuario | null>(null)
const confirmarAbierto = ref(false)
const usuarioBorrando = ref<Usuario | null>(null)
const borrando = ref(false)

function nuevo() {
  usuarioEditando.value = null
  formularioAbierto.value = true
}
function editar(u: Usuario) {
  usuarioEditando.value = u
  formularioAbierto.value = true
}
function pedirBorrado(u: Usuario) {
  usuarioBorrando.value = u
  confirmarAbierto.value = true
}
async function borrar() {
  if (!usuarioBorrando.value) return
  borrando.value = true
  try {
    await api(`/api/usuarios/usuarios/${usuarioBorrando.value.id}`, { method: 'DELETE' })
    notificar('Usuario eliminado')
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
      <h1 class="text-h4">Usuarios</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-account-plus" @click="nuevo">Nuevo usuario</v-btn>
    </div>

    <v-card>
      <v-card-text>
        <v-row dense>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="textoBusqueda"
              label="Buscar por username o email"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              maxlength="50"
            />
          </v-col>
          <v-col cols="6" md="3">
            <v-select v-model="rolFiltro" :items="opcionesRol" label="Rol" clearable hide-details />
          </v-col>
          <v-col cols="6" md="3">
            <v-select v-model="estadoFiltro" :items="opcionesEstado" label="Estado" clearable hide-details />
          </v-col>
        </v-row>
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
        no-data-text="No hay usuarios"
      >
        <template #[`item.rol`]="{ item }">
          <v-chip size="small" :color="item.rol === 'admin' ? 'primary' : undefined">{{ item.rol }}</v-chip>
        </template>
        <template #[`item.activo`]="{ item }">
          <v-chip size="small" variant="tonal" :color="estado(item).color">{{ estado(item).texto }}</v-chip>
        </template>
        <template #[`item.acciones`]="{ item }">
          <template v-if="!item.eliminado_en">
            <v-btn icon="mdi-pencil" variant="text" size="small" aria-label="Editar" @click="editar(item)" />
            <v-btn
              v-if="item.id !== yo?.id"
              icon="mdi-delete"
              variant="text"
              size="small"
              color="error"
              aria-label="Eliminar"
              @click="pedirBorrado(item)"
            />
          </template>
        </template>
      </v-data-table-server>
    </v-card>

    <UsuarioFormulario
      v-model="formularioAbierto"
      :usuario="usuarioEditando"
      :id-propio="yo?.id"
      @guardado="lista.recargar()"
    />
    <ConfirmarDialogo
      v-model="confirmarAbierto"
      titulo="Eliminar usuario"
      :texto="`«${usuarioBorrando?.username}» no podrá volver a iniciar sesión. Su username y email quedarán reservados.`"
      :cargando="borrando"
      @confirmar="borrar"
    />
  </div>
</template>
