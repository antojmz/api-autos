/**
 * utils/formato.ts — Formato de fechas y precios para mostrar.
 * Los archivos de app/utils/ se importan automáticamente en toda la app.
 */

/** Fecha de HOY en formato "AAAA-MM-DD" según la zona horaria local. */
export function hoyISO(): string {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

/**
 * "2026-01-10" -> "10/01/2026". Se trabaja con el texto (sin `new Date`)
 * para evitar desfases de un día por la zona horaria.
 */
export function formatearFecha(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [anio, mes, dia] = iso.slice(0, 10).split('-')
  return `${dia}/${mes}/${anio}`
}

const formatoPrecio = new Intl.NumberFormat('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** "25990.50" -> "$ 25.990,50". La API envía el precio como texto para no perder precisión. */
export function formatearPrecio(precio: string | number): string {
  return `$ ${formatoPrecio.format(Number(precio))}`
}
