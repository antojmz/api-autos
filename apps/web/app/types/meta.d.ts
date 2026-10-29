/**
 * Campos propios de `definePageMeta` que usa middleware/auth.global.ts.
 * Declararlos aquí da autocompletado y detecta errores de escritura.
 */
declare module '#app' {
  interface PageMeta {
    /** Página accesible sin sesión (login, registro). */
    publica?: boolean
    /** Página solo para usuarios con rol admin. */
    soloAdmin?: boolean
  }
}

export {}
