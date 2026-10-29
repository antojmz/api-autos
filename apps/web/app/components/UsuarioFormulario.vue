<!--
  UsuarioFormulario — Diálogo de administración de usuarios (solo admin).
  - Crear:  POST  /api/usuarios/usuarios      (con contraseña y rol)
  - Editar: PATCH /api/usuarios/usuarios/{id} (actualización PARCIAL: solo se
            envían los campos que cambiaron; la contraseña solo si se escribe
            una nueva, y la API la vuelve a hashear)
-->
<script setup lang="ts">
import type { Rol, Usuario } from '#shared/types/api'

const props = defineProps<{ usuario: Usuario | null; idPropio?: number }>()
const abierto = defineModel<boolean>({ required: true })
const emit = defineEmits<{ guardado: [usuario: Usuario] }>()

const { api } = useApi()
const { notificar } = useNotificacion()
const formulario = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const guardando = ref(false)
const verPassword = ref(false)
const datos = reactive({
  username: '',
  email: '',
  nombre_completo: '',
  rol: 'usuario' as Rol,
  activo: true,
  password: '',
})
const roles = [
  { title: 'Usuario', value: 'usuario' },
  { title: 'Administrador', value: 'admin' },
]
const editando = computed(() => props.usuario !== null)
// Un admin no puede quitarse su rol ni desactivarse (la API respondería 400).
const esElMismo = computed(() => props.usuario?.id === props.idPropio)

watch(abierto, (valor) => {
  if (!valor) return
  datos.username = props.usuario?.username ?? ''
  datos.email = props.usuario?.email ?? ''
  datos.nombre_completo = props.usuario?.nombre_completo ?? ''
  datos.rol = props.usuario?.rol ?? 'usuario'
  datos.activo = props.usuario?.activo ?? true
  datos.password = ''
})

/** Solo los campos modificados (PATCH). */
function cambios(): Record<string, unknown> {
  const u = props.usuario!
  const resultado: Record<string, unknown> = {}
  const username = datos.username.trim().toLowerCase()
  const email = datos.email.trim().toLowerCase()
  if (username !== u.username) resultado.username = username
  if (email !== u.email) resultado.email = email
  if (datos.nombre_completo.trim() !== u.nombre_completo) resultado.nombre_completo = datos.nombre_completo.trim()
  if (datos.rol !== u.rol) resultado.rol = datos.rol
  if (datos.activo !== u.activo) resultado.activo = datos.activo
  if (datos.password) resultado.password = datos.password
  return resultado
}

async function guardar() {
  if (!(await formulario.value?.validate())?.valid) return
  guardando.value = true
  try {
    let usuario: Usuario
    if (props.usuario) {
      const cuerpo = cambios()
      if (Object.keys(cuerpo).length === 0) {
        abierto.value = false
        return
      }
      usuario = await api<Usuario>(`/api/usuarios/usuarios/${props.usuario.id}`, { method: 'PATCH', body: cuerpo })
      notificar('Usuario actualizado')
    } else {
      usuario = await api<Usuario>('/api/usuarios/usuarios', {
        method: 'POST',
        body: {
          username: datos.username.trim().toLowerCase(),
          email: datos.email.trim().toLowerCase(),
          nombre_completo: datos.nombre_completo.trim(),
          password: datos.password,
          rol: datos.rol,
        },
      })
      notificar('Usuario creado')
    }
    emit('guardado', usuario)
    abierto.value = false
  } catch {
    // useApi ya mostró el mensaje de error.
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <v-dialog v-model="abierto" max-width="560" persistent>
    <v-card :title="editando ? 'Editar usuario' : 'Nuevo usuario'" prepend-icon="mdi-account">
      <v-form ref="formulario" @submit.prevent="guardar">
        <v-card-text>
          <v-text-field
            v-model="datos.username"
            label="Username"
            autocomplete="off"
            :rules="[reglas.requerido, reglas.longitud(3, 30), reglas.username]"
          />
          <v-text-field v-model="datos.email" label="Email" type="email" :rules="[reglas.requerido, reglas.email]" />
          <v-text-field
            v-model="datos.nombre_completo"
            label="Nombre completo"
            :rules="[reglas.requerido, reglas.longitud(2, 100), reglas.nombreCompleto]"
          />
          <v-select
            v-model="datos.rol"
            :items="roles"
            label="Rol"
            :disabled="esElMismo"
            :hint="esElMismo ? 'No puedes cambiar tu propio rol' : undefined"
            persistent-hint
          />
          <v-switch
            v-if="editando"
            v-model="datos.activo"
            label="Cuenta activa"
            color="primary"
            :disabled="esElMismo"
            hide-details
            class="mt-2"
          />
          <v-text-field
            v-model="datos.password"
            :label="editando ? 'Nueva contraseña (opcional)' : 'Contraseña'"
            :type="verPassword ? 'text' : 'password'"
            :append-inner-icon="verPassword ? 'mdi-eye-off' : 'mdi-eye'"
            autocomplete="new-password"
            class="mt-4"
            :hint="editando ? 'Déjala vacía para no cambiarla' : '10 a 128 caracteres, con letras y números'"
            persistent-hint
            :rules="editando ? [(v: unknown) => !v || reglas.password(v)] : [reglas.password]"
            @click:append-inner="verPassword = !verPassword"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn :disabled="guardando" @click="abierto = false">Cancelar</v-btn>
          <v-btn type="submit" color="primary" variant="flat" :loading="guardando">Guardar</v-btn>
        </v-card-actions>
      </v-form>
    </v-card>
  </v-dialog>
</template>
