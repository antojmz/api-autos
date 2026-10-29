<!--
  ModeloFormulario — Diálogo para crear o editar un modelo.
  - Crear:  POST /api/autos/modelo        (hay que elegir el auto)
  - Editar: PUT  /api/autos/modelos/{id}  (el auto no se puede cambiar)
  Props:
    modelo  -> el modelo a editar, o null para crear.
    autoId  -> auto preseleccionado al crear.
    fijarAuto -> no permite cambiar el auto (p. ej. desde el detalle de un auto).
    autos   -> lista de autos para el selector.
-->
<script setup lang="ts">
import type { Auto, Modelo } from '#shared/types/api'

const props = defineProps<{ modelo: Modelo | null; autoId?: number | null; fijarAuto?: boolean; autos: Auto[] }>()
const abierto = defineModel<boolean>({ required: true })
const emit = defineEmits<{ guardado: [modelo: Modelo] }>()

const { api } = useApi()
const { notificar } = useNotificacion()
const formulario = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
const guardando = ref(false)
const datos = reactive({
  auto_id: null as number | null,
  nombre: '',
  anio: new Date().getFullYear() as number | string,
  precio: '' as string | number,
  fecha_ingreso: hoyISO(),
})

const opcionesAutos = computed(() => props.autos.map((a) => ({ title: `#${a.id} · ${a.marca}`, value: a.id })))
// La fecha del modelo no puede ser anterior a la de su auto (regla del backend).
const autoElegido = computed(() => props.autos.find((a) => a.id === datos.auto_id))

watch(abierto, (valor) => {
  if (!valor) return
  datos.auto_id = props.modelo?.auto_id ?? props.autoId ?? null
  datos.nombre = props.modelo?.nombre ?? ''
  datos.anio = props.modelo?.anio ?? new Date().getFullYear()
  datos.precio = props.modelo?.precio ?? ''
  datos.fecha_ingreso = props.modelo?.fecha_ingreso ?? hoyISO()
})

async function guardar() {
  if (!(await formulario.value?.validate())?.valid) return
  guardando.value = true
  try {
    // El precio viaja como texto ("25990.50"): la API lo convierte a Decimal sin perder precisión.
    const cuerpo = {
      nombre: datos.nombre.trim(),
      anio: Number(datos.anio),
      precio: String(datos.precio).trim(),
      fecha_ingreso: datos.fecha_ingreso,
    }
    const modelo = props.modelo
      ? await api<Modelo>(`/api/autos/modelos/${props.modelo.id}`, { method: 'PUT', body: cuerpo })
      : await api<Modelo>('/api/autos/modelo', { method: 'POST', body: { ...cuerpo, auto_id: datos.auto_id } })
    notificar(props.modelo ? 'Modelo actualizado' : 'Modelo creado')
    emit('guardado', modelo)
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
    <v-card :title="modelo ? 'Editar modelo' : 'Nuevo modelo'" prepend-icon="mdi-car-info">
      <v-form ref="formulario" @submit.prevent="guardar">
        <v-card-text>
          <v-select
            v-model="datos.auto_id"
            :items="opcionesAutos"
            label="Auto"
            :disabled="!!modelo || fijarAuto"
            :hint="modelo ? 'Un modelo no se puede cambiar de auto' : undefined"
            persistent-hint
            :rules="[(v: unknown) => v != null || 'Elige un auto']"
          />
          <v-text-field
            v-model="datos.nombre"
            label="Nombre"
            class="mt-2"
            counter="60"
            :rules="[reglas.requerido, reglas.longitud(1, 60), reglas.textoSeguro]"
          />
          <v-row>
            <v-col cols="12" sm="6">
              <v-text-field v-model="datos.anio" label="Año" type="number" :rules="[reglas.requerido, reglas.anio]" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model="datos.precio"
                label="Precio"
                prefix="$"
                inputmode="decimal"
                :rules="[reglas.requerido, reglas.precio]"
              />
            </v-col>
          </v-row>
          <v-text-field
            v-model="datos.fecha_ingreso"
            label="Fecha de ingreso"
            type="date"
            :min="autoElegido?.fecha_ingreso"
            :max="hoyISO()"
            :rules="[
              reglas.requerido,
              reglas.fechaNoFutura,
              (v: unknown) =>
                !autoElegido || String(v) >= autoElegido.fecha_ingreso || 'No puede ser anterior al ingreso del auto',
            ]"
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
