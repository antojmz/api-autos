<!--
  pages/perfil.vue — Mis datos (PATCH /usuarios/me) y cambio de contraseña
  (PUT /usuarios/me/password). El rol y el estado no se pueden cambiar aquí.
-->
<script setup lang="ts">
import type { Usuario } from '#shared/types/api'

useHead({ title: 'Mi perfil' })
const { usuario } = useAuth()
const { api } = useApi()
const { notificar } = useNotificacion()

type Formulario = { validate: () => Promise<{ valid: boolean }>; reset: () => void }

// --- Datos personales ---
const formularioDatos = ref<Formulario | null>(null)
const datos = reactive({
  username: usuario.value?.username ?? '',
  email: usuario.value?.email ?? '',
  nombre_completo: usuario.value?.nombre_completo ?? '',
})
const guardandoDatos = ref(false)

async function guardarDatos() {
  if (!usuario.value || !(await formularioDatos.value?.validate())?.valid) return
  // Solo se envían los campos que cambiaron (PATCH = actualización parcial).
  const cambios: Record<string, string> = {}
  const username = datos.username.trim().toLowerCase()
  const email = datos.email.trim().toLowerCase()
  if (username !== usuario.value.username) cambios.username = username
  if (email !== usuario.value.email) cambios.email = email
  if (datos.nombre_completo.trim() !== usuario.value.nombre_completo) cambios.nombre_completo = datos.nombre_completo.trim()
  if (Object.keys(cambios).length === 0) return notificar('No hay cambios', 'info')

  guardandoDatos.value = true
  try {
    usuario.value = await api<Usuario>('/api/usuarios/usuarios/me', { method: 'PATCH', body: cambios })
    notificar('Datos actualizados')
  } catch {
    // useApi ya mostró el error.
  } finally {
    guardandoDatos.value = false
  }
}

// --- Contraseña ---
const formularioPassword = ref<Formulario | null>(null)
const password = reactive({ actual: '', nueva: '', confirmar: '' })
const verPassword = ref(false)
const guardandoPassword = ref(false)

async function cambiarPassword() {
  if (!(await formularioPassword.value?.validate())?.valid) return
  guardandoPassword.value = true
  try {
    await api('/api/usuarios/usuarios/me/password', {
      method: 'PUT',
      body: { password_actual: password.actual, password_nueva: password.nueva },
    })
    notificar('Contraseña cambiada')
    formularioPassword.value?.reset()
  } catch {
    // useApi ya mostró el error (p. ej. "La contraseña actual no es correcta").
  } finally {
    guardandoPassword.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Mi perfil</h1>
    <v-row>
      <v-col cols="12" md="6">
        <v-card title="Mis datos" prepend-icon="mdi-account-edit">
          <v-form ref="formularioDatos" @submit.prevent="guardarDatos">
            <v-card-text>
              <v-text-field
                v-model="datos.username"
                label="Username"
                :rules="[reglas.requerido, reglas.longitud(3, 30), reglas.username]"
              />
              <v-text-field v-model="datos.email" label="Email" type="email" :rules="[reglas.requerido, reglas.email]" />
              <v-text-field
                v-model="datos.nombre_completo"
                label="Nombre completo"
                :rules="[reglas.requerido, reglas.longitud(2, 100), reglas.nombreCompleto]"
              />
              <div class="text-body-2 text-medium-emphasis">
                Rol: <strong>{{ usuario?.rol }}</strong> · Alta: {{ formatearFecha(usuario?.creado_en) }}
              </div>
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn type="submit" color="primary" variant="flat" :loading="guardandoDatos">Guardar</v-btn>
            </v-card-actions>
          </v-form>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card title="Cambiar contraseña" prepend-icon="mdi-lock-reset">
          <v-form ref="formularioPassword" @submit.prevent="cambiarPassword">
            <v-card-text>
              <v-text-field
                v-model="password.actual"
                label="Contraseña actual"
                :type="verPassword ? 'text' : 'password'"
                autocomplete="current-password"
                :rules="[reglas.requerido]"
              />
              <v-text-field
                v-model="password.nueva"
                label="Nueva contraseña"
                :type="verPassword ? 'text' : 'password'"
                autocomplete="new-password"
                hint="10 a 128 caracteres, con letras y números"
                :rules="[reglas.password, (v: unknown) => v !== password.actual || 'Debe ser distinta de la actual']"
              />
              <v-text-field
                v-model="password.confirmar"
                label="Repite la nueva contraseña"
                :type="verPassword ? 'text' : 'password'"
                autocomplete="new-password"
                :rules="[(v: unknown) => v === password.nueva || 'Las contraseñas no coinciden']"
              />
              <v-checkbox v-model="verPassword" label="Mostrar contraseñas" hide-details density="compact" />
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn type="submit" color="primary" variant="flat" :loading="guardandoPassword">Cambiar</v-btn>
            </v-card-actions>
          </v-form>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
