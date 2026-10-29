<!--
  layouts/default.vue — Estructura de las páginas privadas: barra superior,
  menú lateral y contenido. Las opciones de admin solo se muestran a admins
  (las APIs igualmente rechazan con 403 a quien no lo sea).
-->
<script setup lang="ts">
import { useDisplay, useTheme } from 'vuetify'

const { usuario, esAdmin, logout } = useAuth()
const theme = useTheme()
const { mobile } = useDisplay()
const menuAbierto = ref<boolean | null>(null)

const temaCookie = useCookie<'light' | 'dark'>('tema', { sameSite: 'lax' })
const esOscuro = computed(() => theme.global.current.value.dark)
function alternarTema() {
  const nuevo = esOscuro.value ? 'light' : 'dark'
  theme.change(nuevo)
  temaCookie.value = nuevo
}

const opciones = computed(() => [
  { titulo: 'Inicio', icono: 'mdi-view-dashboard-outline', ruta: '/' },
  { titulo: 'Autos', icono: 'mdi-car', ruta: '/autos' },
  { titulo: 'Modelos', icono: 'mdi-car-info', ruta: '/modelos' },
  ...(esAdmin.value ? [{ titulo: 'Usuarios', icono: 'mdi-account-group', ruta: '/usuarios' }] : []),
])
</script>

<template>
  <v-navigation-drawer v-model="menuAbierto" :temporary="mobile">
    <v-list-item
      class="py-4"
      prepend-icon="mdi-car-multiple"
      title="Concesionario"
      subtitle="Gestión de autos"
    />
    <v-divider />
    <v-list nav density="comfortable">
      <v-list-item
        v-for="op in opciones"
        :key="op.ruta"
        :to="op.ruta"
        :prepend-icon="op.icono"
        :title="op.titulo"
        :exact="op.ruta === '/'"
      />
    </v-list>
  </v-navigation-drawer>

  <v-app-bar flat border="b">
    <v-app-bar-nav-icon aria-label="Menú" @click="menuAbierto = !menuAbierto" />
    <v-app-bar-title>Concesionario</v-app-bar-title>

    <v-btn
      :icon="esOscuro ? 'mdi-weather-sunny' : 'mdi-weather-night'"
      :aria-label="esOscuro ? 'Tema claro' : 'Tema oscuro'"
      @click="alternarTema"
    />

    <v-menu v-if="usuario">
      <template #activator="{ props }">
        <v-btn v-bind="props" prepend-icon="mdi-account-circle" class="text-none">
          {{ usuario.username }}
          <v-chip v-if="esAdmin" size="x-small" color="primary" class="ml-2">admin</v-chip>
        </v-btn>
      </template>
      <v-list density="compact">
        <v-list-item :subtitle="usuario.email" :title="usuario.nombre_completo" />
        <v-divider />
        <v-list-item to="/perfil" prepend-icon="mdi-account-edit" title="Mi perfil" />
        <v-list-item prepend-icon="mdi-logout" title="Cerrar sesión" @click="logout()" />
      </v-list>
    </v-menu>
  </v-app-bar>

  <v-main>
    <v-container class="py-6" max-width="1200">
      <slot />
    </v-container>
  </v-main>
</template>
