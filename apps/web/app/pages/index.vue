<!-- pages/index.vue — Inicio: totales y accesos rápidos. -->
<script setup lang="ts">
import type { Pagina } from '#shared/types/api'

useHead({ title: 'Inicio' })
const { usuario, esAdmin } = useAuth()
const requestFetch = useRequestFetch()

/** Pide solo 1 elemento: lo que interesa es el `total` de la página. */
const contar = (url: string) =>
  requestFetch<Pagina<unknown>>(url, { query: { limit: 1 } })
    .then((p) => p.total)
    .catch(() => null)

const { data: totales } = await useAsyncData('totales', async () => {
  const [autos, modelos, usuarios] = await Promise.all([
    contar('/api/autos/autos'),
    contar('/api/autos/modelos'),
    esAdmin.value ? contar('/api/usuarios/usuarios') : Promise.resolve(null),
  ])
  return { autos, modelos, usuarios }
})

const tarjetas = computed(() => [
  { titulo: 'Autos', icono: 'mdi-car', total: totales.value?.autos, ruta: '/autos' },
  { titulo: 'Modelos', icono: 'mdi-car-info', total: totales.value?.modelos, ruta: '/modelos' },
  ...(esAdmin.value
    ? [{ titulo: 'Usuarios', icono: 'mdi-account-group', total: totales.value?.usuarios, ruta: '/usuarios' }]
    : []),
])
</script>

<template>
  <div>
    <h1 class="text-h4 mb-1">Hola, {{ usuario?.nombre_completo }}</h1>
    <p class="text-medium-emphasis mb-6">
      Rol: <strong>{{ esAdmin ? 'administrador' : 'usuario' }}</strong>
    </p>

    <v-row>
      <v-col v-for="t in tarjetas" :key="t.ruta" cols="12" sm="6" md="4">
        <v-card :to="t.ruta" variant="tonal" color="primary">
          <v-card-item>
            <template #prepend><v-icon :icon="t.icono" size="40" /></template>
            <v-card-title>{{ t.titulo }}</v-card-title>
            <v-card-subtitle>Ver y gestionar</v-card-subtitle>
          </v-card-item>
          <v-card-text class="text-h3">{{ t.total ?? '—' }}</v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>
