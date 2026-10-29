/**
 * utils/reglas.ts — Reglas de validación para los formularios de Vuetify.
 *
 * Son las MISMAS reglas que aplican los backends (schemas.py), para avisar al
 * usuario antes de enviar. La validación del cliente es solo comodidad: un
 * usuario puede saltársela, por eso las APIs vuelven a validar todo.
 *
 * Una regla de Vuetify es una función que recibe el valor y devuelve `true`
 * si es válido o un texto con el error.
 */
type Regla = (valor: unknown) => true | string

const LETRA_O_DIGITO = 'A-Za-zÀ-ÖØ-öø-ÿ0-9'
// Igual que PATRON_TEXTO_SEGURO de api-autos: palabras separadas por un espacio, punto o guion.
const PATRON_TEXTO_SEGURO = new RegExp(`^[${LETRA_O_DIGITO}]+(?:[ .\\-][${LETRA_O_DIGITO}]+)*$`)
const PATRON_USERNAME = /^[a-z0-9]+(?:[._-][a-z0-9]+)*$/
const PATRON_NOMBRE_COMPLETO = /^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[ .'-]{1,2}[A-Za-zÀ-ÖØ-öø-ÿ]+)*\.?$/
const PATRON_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PRECIO_MAXIMO = 99_999_999.99
export const ANIO_MINIMO = 1886

const texto = (v: unknown) => (typeof v === 'string' ? v.trim() : v == null ? '' : String(v))

export const reglas = {
  requerido: ((v) => texto(v) !== '' || 'Campo obligatorio') as Regla,

  longitud: (min: number, max: number): Regla => (v) => {
    const n = texto(v).length
    return (n >= min && n <= max) || `Debe tener entre ${min} y ${max} caracteres`
  },

  textoSeguro: ((v) =>
    PATRON_TEXTO_SEGURO.test(texto(v)) || 'Solo letras, números y separadores simples (espacio, punto, guion)') as Regla,

  fechaNoFutura: ((v) => !v || texto(v) <= hoyISO() || 'La fecha no puede ser futura') as Regla,

  anio: ((v) => {
    const n = Number(v)
    const maximo = new Date().getFullYear() + 1
    return (Number.isInteger(n) && n >= ANIO_MINIMO && n <= maximo) || `Año entre ${ANIO_MINIMO} y ${maximo}`
  }) as Regla,

  precio: ((v) => {
    const s = texto(v)
    const n = Number(s)
    if (!/^\d+(\.\d{1,2})?$/.test(s)) return 'Número positivo con hasta 2 decimales'
    return (n > 0 && n <= PRECIO_MAXIMO) || 'El precio debe ser mayor que 0 y como máximo 99.999.999,99'
  }) as Regla,

  username: ((v) =>
    PATRON_USERNAME.test(texto(v).toLowerCase()) || 'Letras, números y . _ - entre palabras') as Regla,

  email: ((v) => PATRON_EMAIL.test(texto(v)) || 'Email no válido') as Regla,

  nombreCompleto: ((v) => PATRON_NOMBRE_COMPLETO.test(texto(v)) || 'Solo letras, espacios, puntos, apóstrofes y guiones') as Regla,

  // La contraseña NO se recorta: los espacios son parte de ella.
  password: ((v) => {
    const s = typeof v === 'string' ? v : ''
    if (s.length < 10 || s.length > 128) return 'Entre 10 y 128 caracteres'
    return (/[A-Za-zÀ-ÿ]/.test(s) && /\d/.test(s)) || 'Debe incluir al menos una letra y un número'
  }) as Regla,
}
