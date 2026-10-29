<!-- pages/registro.vue — Registro público. La cuenta se crea con rol "usuario". -->
<script setup lang="ts">
definePageMeta({ layout: 'auth', publica: true })
useHead({ title: 'Crear cuenta' })

const { registro, login } = useAuth()
const { notificar } = useNotificacion()
const formulario = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const datos = reactive({ username: '', email: '', nombre_completo: '', password: '', confirmar: '' })
const verPassword = ref(false)
const cargando = ref(false)
const error = ref('')

async function registrar() {
  if (!(await formulario.value?.validate())?.valid) return
  error.value = ''
  cargando.value = true
  try {
    const username = datos.username.trim().toLowerCase()
    await registro({
      username,
      email: datos.email.trim().toLowerCase(),
      nombre_completo: datos.nombre_completo.trim(),
      password: datos.password,
    })
    // Tras registrarse, se inicia sesión automáticamente.
    await login(username, datos.password)
    notificar('¡Cuenta creada!')
    await navigateTo('/')
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <v-card title="Crear cuenta" class="pa-2">
    <v-form ref="formulario" @submit.prevent="registrar">
      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4" :text="error" />
        <v-text-field
          v-model="datos.username"
          label="Username"
          autocomplete="username"
          hint="3 a 30 caracteres: letras, números y . _ -"
          :rules="[reglas.requerido, reglas.longitud(3, 30), reglas.username]"
        />
        <v-text-field v-model="datos.email" label="Email" type="email" autocomplete="email" :rules="[reglas.requerido, reglas.email]" />
        <v-text-field
          v-model="datos.nombre_completo"
          label="Nombre completo"
          autocomplete="name"
          :rules="[reglas.requerido, reglas.longitud(2, 100), reglas.nombreCompleto]"
        />
        <v-text-field
          v-model="datos.password"
          label="Contraseña"
          :type="verPassword ? 'text' : 'password'"
          :append-inner-icon="verPassword ? 'mdi-eye-off' : 'mdi-eye'"
          autocomplete="new-password"
          hint="10 a 128 caracteres, con letras y números"
          :rules="[reglas.password]"
          @click:append-inner="verPassword = !verPassword"
        />
        <v-text-field
          v-model="datos.confirmar"
          label="Repite la contraseña"
          :type="verPassword ? 'text' : 'password'"
          autocomplete="new-password"
          :rules="[(v: unknown) => v === datos.password || 'Las contraseñas no coinciden']"
        />
        <v-btn type="submit" color="primary" variant="flat" block size="large" :loading="cargando">Crear cuenta</v-btn>
      </v-card-text>
    </v-form>
    <v-card-text class="text-center pt-0">
      ¿Ya tienes cuenta? <NuxtLink to="/login">Inicia sesión</NuxtLink>
    </v-card-text>
  </v-card>
</template>
