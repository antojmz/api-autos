"""
schemas.py — Modelos Pydantic de entrada y salida (el "contrato" de la API).

Concepto clave de FastAPI: cuando un endpoint declara un parámetro cuyo tipo es
un modelo Pydantic, FastAPI automáticamente:
  1. Lee el cuerpo JSON de la petición.
  2. Lo valida contra el modelo (tipos, longitudes, rangos, patrones).
  3. Si algo falla, responde 422 SIN ejecutar tu código.
  4. Documenta el modelo en OpenAPI (/docs).

OWASP — Validación estricta de entradas:
  - `extra="forbid"`: rechaza campos no declarados (evita "mass assignment").
  - `str_strip_whitespace=True`: elimina espacios al inicio/fin.
  - Longitudes mínimas/máximas, patrones de caracteres permitidos (lista
    blanca) y rangos numéricos razonables.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constantes de validación
# ---------------------------------------------------------------------------
ANIO_MINIMO = 1886  # año del primer automóvil (Benz Patent-Motorwagen)
PRECIO_MAXIMO = Decimal("99999999.99")  # coincide con NUMERIC(12, 2)

# Lista blanca de caracteres: letras (incluidas tildes y ñ), dígitos y
# separadores simples (espacio, punto, guion) entre palabras.
# Ej. válidos: "Toyota", "Mercedes-Benz", "Citroën C3". Inválidos: "<script>",
# "a;DROP TABLE", "  ", "--".
_LETRA_O_DIGITO = r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]"
PATRON_TEXTO_SEGURO = rf"^{_LETRA_O_DIGITO}+(?:[ .\-]{_LETRA_O_DIGITO}+)*$"


# ---------------------------------------------------------------------------
# Validadores reutilizables
# ---------------------------------------------------------------------------
# `Annotated[tipo, ...]` permite "adjuntar" reglas a un tipo y reutilizarlo.
# `AfterValidator` ejecuta una función después de la validación básica de tipo.
def _no_futura(valor: date) -> date:
    if valor > date.today():
        raise ValueError("la fecha de ingreso no puede ser futura")
    return valor


def _anio_razonable(valor: int) -> int:
    # Se calcula en cada validación (no al importar) para que el límite avance
    # solo cuando cambia el año. Se permite el modelo del año siguiente.
    maximo = date.today().year + 1
    if valor > maximo:
        raise ValueError(f"el año no puede ser mayor que {maximo}")
    return valor


FechaIngreso = Annotated[date, AfterValidator(_no_futura)]
Marca = Annotated[str, Field(min_length=2, max_length=50, pattern=PATRON_TEXTO_SEGURO)]


class EntradaEstricta(BaseModel):
    """Configuración común a todos los modelos que recibe la API."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SalidaORM(BaseModel):
    """
    Configuración común a los modelos de respuesta.
    `from_attributes=True` permite construirlos a partir de objetos del ORM
    (lee `objeto.marca` en vez de `dict["marca"]`).
    """

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Autos
# ---------------------------------------------------------------------------
class AutoCreate(EntradaEstricta):
    """Cuerpo de POST /autos."""

    marca: Marca = Field(examples=["Toyota"])
    # Si no se envía, se usa la fecha de hoy. `default_factory` evalúa la
    # función en cada petición (no una sola vez al arrancar).
    fecha_ingreso: FechaIngreso = Field(default_factory=date.today)


class AutoUpdate(EntradaEstricta):
    """Cuerpo de PUT /autos/{id}. PUT = reemplazo completo: todo es obligatorio."""

    marca: Marca = Field(examples=["Toyota"])
    fecha_ingreso: FechaIngreso


class ModeloPublic(SalidaORM):
    id: int
    auto_id: int
    nombre: str
    anio: int
    # En la respuesta JSON, Pydantic serializa Decimal como string ("25990.00")
    # para no perder precisión.
    precio: Decimal
    fecha_ingreso: date


class AutoPublic(SalidaORM):
    """Lo que devolvemos al cliente: nunca el objeto ORM directamente."""

    id: int
    marca: str
    fecha_ingreso: date


class AutoConModelos(AutoPublic):
    modelos: list[ModeloPublic]


class Pagina[T](BaseModel):
    """
    Modelo genérico de paginación (sintaxis de genéricos de Python 3.12+).
    `Pagina[AutoPublic]` y `Pagina[AutoConModelos]` reutilizan la misma forma.
    """

    total: int = Field(description="Total de registros que cumplen el filtro")
    skip: int
    limit: int
    items: list[T]


# ---------------------------------------------------------------------------
# Modelos (de auto)
# ---------------------------------------------------------------------------
# Tipos reutilizables de los campos de un modelo: los usan tanto la creación
# (POST /modelo) como la actualización (PUT /modelos/{id}), así las reglas
# están escritas una sola vez.
NombreModelo = Annotated[
    str, Field(min_length=1, max_length=60, pattern=PATRON_TEXTO_SEGURO, examples=["Corolla"])
]
AnioModelo = Annotated[int, Field(ge=ANIO_MINIMO, examples=[2024]), AfterValidator(_anio_razonable)]
# gt=0: precio estrictamente positivo. max_digits / decimal_places coinciden
# con la columna NUMERIC(12, 2) para no truncar valores.
PrecioModelo = Annotated[
    Decimal, Field(gt=0, le=PRECIO_MAXIMO, max_digits=12, decimal_places=2, examples=[25990.00])
]


class ModeloCreate(EntradaEstricta):
    """Cuerpo de POST /modelo."""

    auto_id: int = Field(gt=0, examples=[1])
    nombre: NombreModelo
    anio: AnioModelo
    precio: PrecioModelo
    fecha_ingreso: FechaIngreso = Field(default_factory=date.today)


class ModeloUpdate(EntradaEstricta):
    """
    Cuerpo de PUT /modelos/{id}. PUT = reemplazo completo: todo es obligatorio.
    No incluye `auto_id`: un modelo no se puede mover a otro auto (y como
    extra="forbid", enviarlo devuelve 422).
    """

    nombre: NombreModelo
    anio: AnioModelo
    precio: PrecioModelo
    fecha_ingreso: FechaIngreso
