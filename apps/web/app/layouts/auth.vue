<!-- layouts/auth.vue — Pantallas públicas (login, registro): tarjeta centrada. -->
<template>
  <v-main class="d-flex align-center justify-center" style="min-height: 100vh">
    <v-container max-width="460">
      <div class="text-center mb-6">
        <v-icon icon="mdi-car-multiple" size="48" color="primary" />
        <h1 class="text-h5 mt-2">Concesionario</h1>
      </div>
      <slot />
    </v-container>
  </v-main>
</template>
