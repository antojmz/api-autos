<!--
  ConfirmarDialogo — Pide confirmación antes de una acción destructiva.
  Uso: <ConfirmarDialogo v-model="abierto" titulo="..." texto="..." @confirmar="borrar" />
-->
<script setup lang="ts">
defineProps<{ titulo: string; texto: string; cargando?: boolean; textoBoton?: string }>()
const abierto = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirmar: [] }>()
</script>

<template>
  <v-dialog v-model="abierto" max-width="440">
    <v-card :title="titulo" prepend-icon="mdi-alert-outline">
      <v-card-text>{{ texto }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn :disabled="cargando" @click="abierto = false">Cancelar</v-btn>
        <v-btn color="error" variant="flat" :loading="cargando" @click="emit('confirmar')">
          {{ textoBoton ?? 'Eliminar' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
