<!--
  AutoFormulario — Diálogo para crear o editar un auto.
  - Sin `auto`  -> crea:  POST /api/autos/autos
  - Con `auto`  -> edita: PUT  /api/autos/autos/{id} (reemplazo completo)
  Emite `guardado` con el auto que devolvió la API.
-->
<script setup lang="ts">
import type { Auto } from '#shared/types/api'

const props = defineProps<{ auto: Auto | null }>()
const abierto = defineModel<boolean>({ required: true })
const emit = defineEmits<{ guardado: [auto: Auto] }>()

const { api } = useApi()
const { notificar } = useNotificacion()
const formulario = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const guardando = ref(false)
const datos = reactive({ marca: '', fecha_ingreso: hoyISO() })

// Cada vez que se abre, se cargan los datos del auto (o se limpia el formulario).
watch(abierto, (valor) => {
  if (!valor) return
  datos.marca = props.auto?.marca ?? ''
  datos.fecha_ingreso = props.auto?.fecha_ingreso ?? hoyISO()
})

async function guardar() {
  if (!(await formulario.value?.validate())?.valid) return
  guardando.value = true
  try {
    const cuerpo = { marca: datos.marca.trim(), fecha_ingreso: datos.fecha_ingreso }
    const auto = props.auto
      ? await api<Auto>(`/api/autos/autos/${props.auto.id}`, { method: 'PUT', body: cuerpo })
      : await api<Auto>('/api/autos/autos', { method: 'POST', body: cuerpo })
    notificar(props.auto ? 'Auto actualizado' : 'Auto creado')
    emit('guardado', auto)
    abierto.value = false
  } catch {
    // useApi ya mostró el mensaje de error.
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <v-dialog v-model="abierto" max-width="520" persistent>
    <v-card :title="auto ? 'Editar auto' : 'Nuevo auto'" prepend-icon="mdi-car">
      <v-form ref="formulario" @submit.prevent="guardar">
        <v-card-text>
          <v-text-field
            v-model="datos.marca"
            label="Marca"
            autofocus
            counter="50"
            :rules="[reglas.requerido, reglas.longitud(2, 50), reglas.textoSeguro]"
          />
          <v-text-field
            v-model="datos.fecha_ingreso"
            label="Fecha de ingreso"
            type="date"
            :max="hoyISO()"
            :rules="[reglas.requerido, reglas.fechaNoFutura]"
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
