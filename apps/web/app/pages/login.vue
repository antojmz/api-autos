<!-- pages/login.vue — Inicio de sesión (público). -->
<script setup lang="ts">
definePageMeta({ layout: 'auth', publica: true })
useHead({ title: 'Iniciar sesión' })

const { login } = useAuth()
const route = useRoute()
const datos = reactive({ username: '', password: '' })
const verPassword = ref(false)
const cargando = ref(false)
const error = ref('')

/**
 * Solo se permite volver a rutas INTERNAS ("/autos", no "//otro-sitio.com"):
 * evita una "redirección abierta" que un atacante podría usar en un enlace.
 */
function destinoSeguro(): string {
  const r = route.query.redirect
  return typeof r === 'string' && r.startsWith('/') && !r.startsWith('//') ? r : '/'
}

async function entrar() {
  error.value = ''
  cargando.value = true
  try {
    await login(datos.username.trim(), datos.password)
    await navigateTo(destinoSeguro())
  } catch (e) {
    error.value = mensajeDeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <v-card title="Iniciar sesión" class="pa-2">
    <v-form @submit.prevent="entrar">
      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4" :text="error" />
        <v-text-field
          v-model="datos.username"
          label="Username o email"
          prepend-inner-icon="mdi-account"
          autocomplete="username"
          autofocus
          :rules="[reglas.requerido]"
        />
        <v-text-field
          v-model="datos.password"
          label="Contraseña"
          prepend-inner-icon="mdi-lock"
          :type="verPassword ? 'text' : 'password'"
          :append-inner-icon="verPassword ? 'mdi-eye-off' : 'mdi-eye'"
          autocomplete="current-password"
          :rules="[reglas.requerido]"
          @click:append-inner="verPassword = !verPassword"
        />
        <v-btn type="submit" color="primary" variant="flat" block size="large" :loading="cargando">Entrar</v-btn>
      </v-card-text>
    </v-form>
    <v-card-text class="text-center pt-0">
      ¿No tienes cuenta? <NuxtLink to="/registro">Regístrate</NuxtLink>
    </v-card-text>
  </v-card>
</template>
