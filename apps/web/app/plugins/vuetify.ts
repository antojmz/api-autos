/**
 * plugins/vuetify.ts — Registra Vuetify 4 en la aplicación.
 *
 * Los plugins de app/plugins/ se ejecutan al iniciar la app, tanto en el
 * servidor (SSR) como en el navegador. Los componentes de Vuetify se importan
 * solos gracias a vite-plugin-vuetify (ver nuxt.config.ts).
 */
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import { es } from 'vuetify/locale'

export default defineNuxtPlugin((nuxtApp) => {
  // El tema elegido se guarda en una cookie normal (no httpOnly: no es un
  // secreto) para que el servidor pinte la página ya con el tema correcto.
  const tema = useCookie<'light' | 'dark'>('tema', { default: () => 'light', sameSite: 'lax' })

  const vuetify = createVuetify({
    ssr: true,
    // Textos internos de Vuetify (paginación, "Sin datos"...) en español.
    locale: { locale: 'es', messages: { es } },
    theme: {
      defaultTheme: tema.value,
      themes: {
        light: { colors: { primary: '#1565C0', secondary: '#455A64' } },
        dark: { colors: { primary: '#64B5F6', secondary: '#90A4AE' } },
      },
    },
    // Valores por defecto para que todos los formularios se vean igual.
    defaults: {
      VTextField: { variant: 'outlined', density: 'comfortable' },
      VSelect: { variant: 'outlined', density: 'comfortable' },
      VBtn: { rounded: 'lg' },
      VCard: { rounded: 'lg' },
    },
  })

  nuxtApp.vueApp.use(vuetify)
})
