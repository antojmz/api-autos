"""
auth_jwt — Librería compartida de autenticación con JWT.

La usan:
  - services/api-usuarios: para EMITIR tokens al hacer login.
  - services/api-autos (y futuros servicios): para VALIDAR tokens y proteger
    sus rutas, sin necesidad de llamar a api-usuarios en cada petición.

Se exporta aquí lo que los servicios necesitan, para que importen siempre
desde `auth_jwt` y no desde los módulos internos.
"""

from auth_jwt.config import ConfigJWT, get_config_jwt
from auth_jwt.fastapi_deps import ClaimsDep, error_401, obtener_claims, requiere_rol
from auth_jwt.tokens import ClaimsToken, Rol, TokenInvalido, crear_token_acceso, decodificar_token

__all__ = [
    "ClaimsDep",
    "ClaimsToken",
    "ConfigJWT",
    "Rol",
    "TokenInvalido",
    "crear_token_acceso",
    "decodificar_token",
    "error_401",
    "get_config_jwt",
    "obtener_claims",
    "requiere_rol",
]
