<!--
  app.vue — Raíz de la aplicación.
  <v-app> es obligatorio en Vuetify: aplica el tema y organiza el layout.
  <NuxtLayout> elige el layout de la página (layouts/default.vue o auth.vue)
  y <NuxtPage> muestra la página según la URL (carpeta pages/).
-->
<script setup lang="ts">
const { notificacion } = useNotificacion()
</script>

<template>
  <v-app>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>

    <!-- Mensajes globales (useNotificacion). -->
    <v-snackbar v-model="notificacion.visible" :color="notificacion.color" timeout="4000" location="top right">
      {{ notificacion.texto }}
      <template #actions>
        <v-btn variant="text" icon="mdi-close" aria-label="Cerrar" @click="notificacion.visible = false" />
      </template>
    </v-snackbar>
  </v-app>
</template>
