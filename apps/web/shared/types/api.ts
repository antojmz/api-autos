/**
 * shared/types/api.ts — Tipos de los datos que devuelven las APIs.
 *
 * La carpeta shared/ la pueden importar tanto el código del navegador (app/)
 * como el del servidor (server/), con el alias `#shared`. Estos tipos reflejan
 * los esquemas Pydantic de los backends (AutoPublic, ModeloPublic,
 * UsuarioPublic, Pagina[T]...).
 */

/** Respuesta paginada de los listados: {total, skip, limit, items}. */
export interface Pagina<T> {
  total: number
  skip: number
  limit: number
  items: T[]
}

// ---------------------------------------------------------------------------
// api-autos
// ---------------------------------------------------------------------------
export interface Auto {
  id: number
  marca: string
  /** Fecha ISO "AAAA-MM-DD". */
  fecha_ingreso: string
}

export interface Modelo {
  id: number
  auto_id: number
  nombre: string
  anio: number
  /** Decimal serializado como string para no perder precisión ("25990.50"). */
  precio: string
  fecha_ingreso: string
}

export interface AutoConModelos extends Auto {
  modelos: Modelo[]
}

// ---------------------------------------------------------------------------
// api-usuarios
// ---------------------------------------------------------------------------
export type Rol = 'admin' | 'usuario'

/** Datos públicos de un usuario. La API nunca devuelve la contraseña ni su hash. */
export interface Usuario {
  id: number
  username: string
  email: string
  nombre_completo: string
  rol: Rol
  activo: boolean
  creado_en: string
  actualizado_en: string
  eliminado_en: string | null
}

// ---------------------------------------------------------------------------
// Errores (mismo formato en ambas APIs)
// ---------------------------------------------------------------------------
/** Cuerpo de error: `detail` siempre; `errores` solo en los 422 de validación. */
export interface ErrorApi {
  detail: string
  errores?: { campo: string; mensaje: string }[]
}
