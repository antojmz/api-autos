"""
schemas.py — Esquemas Pydantic (DTOs) de entrada y salida de api-usuarios.

Los mismos principios que en api-autos:
  - Entrada: `extra="forbid"` (nadie puede colar campos como `rol` o
    `password_hash` en el registro: "mass assignment") y validación estricta
    de longitudes y caracteres permitidos.
  - Salida: modelos explícitos que NUNCA incluyen `password_hash`. Aunque el
    endpoint devuelva el objeto ORM completo, `response_model` filtra los
    campos y solo se envían los declarados aquí.
"""

from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

from auth_jwt import Rol

# ---------------------------------------------------------------------------
# Validadores reutilizables
# ---------------------------------------------------------------------------
PASSWORD_MIN = 10
PASSWORD_MAX = 128  # límite superior: evita gastar CPU hasheando textos enormes


def _normalizar_identificador(valor: object) -> object:
    """Recorta espacios y pasa a minúsculas ANTES de validar el patrón."""
    return valor.strip().lower() if isinstance(valor, str) else valor


def _password_robusta(valor: str) -> str:
    # Política mínima: longitud (Field) + al menos una letra y un número.
    # OWASP prioriza la longitud sobre reglas de complejidad excesivas.
    if not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
        raise ValueError("la contraseña debe incluir al menos una letra y un número")
    return valor


# username: minúsculas, dígitos y separadores simples (. _ -) entre palabras.
Username = Annotated[
    str,
    BeforeValidator(_normalizar_identificador),
    Field(min_length=3, max_length=30, pattern=r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$", examples=["ana.perez"]),
]
# EmailStr valida el formato con la librería email-validator. Se guarda en
# minúsculas para que la unicidad no dependa de mayúsculas.
Email = Annotated[EmailStr, BeforeValidator(_normalizar_identificador), Field(examples=["ana@example.com"])]
_LETRA = r"[A-Za-zÀ-ÖØ-öø-ÿ]"
NombreCompleto = Annotated[
    str,
    Field(
        min_length=2,
        max_length=100,
        pattern=rf"^{_LETRA}+(?:[ .'\-]{{1,2}}{_LETRA}+)*\.?$",
        examples=["Ana Pérez"],
    ),
]
# Las contraseñas NO se recortan (strip_whitespace=False): un espacio al final
# es parte de la contraseña y cambiarlo impediría al usuario iniciar sesión.
Password = Annotated[
    str,
    StringConstraints(strip_whitespace=False, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX),
    AfterValidator(_password_robusta),
    Field(examples=["Clave-Segura-2026"]),
]


class EntradaEstricta(BaseModel):
    """Configuración común a todo lo que recibe la API."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EntradaParcial(EntradaEstricta):
    """
    Base para actualizaciones parciales (PATCH): todos los campos son
    opcionales, pero si el cliente envía uno, no puede ser null.
    """

    @model_validator(mode="after")
    def _sin_nulos(self) -> Self:
        nulos = [campo for campo in self.model_fields_set if getattr(self, campo) is None]
        if nulos:
            raise ValueError(f"estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


class SalidaORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagina[T](BaseModel):
    total: int = Field(description="Total de registros que cumplen el filtro")
    skip: int
    limit: int
    items: list[T]


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
class RegistroUsuario(EntradaEstricta):
    """POST /auth/registro. No acepta `rol`: todo registro público es 'usuario'."""

    username: Username
    email: Email
    nombre_completo: NombreCompleto
    password: Password


class UsuarioCreateAdmin(RegistroUsuario):
    """POST /usuarios (solo admin): igual que el registro, pero puede fijar el rol."""

    rol: Rol = Rol.USUARIO


class UsuarioUpdateMe(EntradaParcial):
    """PATCH /usuarios/me: el usuario edita sus datos (no su rol ni su estado)."""

    username: Username | None = None
    email: Email | None = None
    nombre_completo: NombreCompleto | None = None


class UsuarioUpdateAdmin(UsuarioUpdateMe):
    """
    PATCH /usuarios/{id} (solo admin). Si incluye `password`, se HASHEA antes
    de guardarla: nunca se escribe la contraseña directamente en la BD.
    """

    rol: Rol | None = None
    activo: bool | None = None
    password: Password | None = None


class CambioPassword(EntradaEstricta):
    """PUT /usuarios/me/password: exige la contraseña actual."""

    password_actual: Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=PASSWORD_MAX)]
    password_nueva: Password

    @model_validator(mode="after")
    def _distintas(self) -> Self:
        if self.password_actual == self.password_nueva:
            raise ValueError("la contraseña nueva debe ser distinta de la actual")
        return self


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------
class UsuarioPublic(SalidaORM):
    """Datos públicos del usuario. Sin `password_hash`, a propósito."""

    id: int
    username: str
    email: str
    nombre_completo: str
    rol: Rol
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    eliminado_en: datetime | None


class Token(BaseModel):
    """Respuesta del login (formato estándar OAuth2)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta que el token expire")
