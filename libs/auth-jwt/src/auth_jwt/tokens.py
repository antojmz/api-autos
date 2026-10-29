"""
tokens.py — Crear y validar JSON Web Tokens (JWT).

Un JWT tiene tres partes separadas por puntos: header.payload.firma
  - header:  algoritmo usado ({"alg": "HS256", "typ": "JWT"}).
  - payload: los "claims", datos sobre el usuario y el token (NO cifrados,
             solo codificados en base64: nunca poner datos sensibles).
  - firma:   HMAC del header+payload con la clave secreta. Si alguien cambia
             un solo carácter del payload, la firma ya no coincide.
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from pydantic import BaseModel, ValidationError

from auth_jwt.config import get_config_jwt


class Rol(StrEnum):
    """Roles del sistema. Compartidos para que todos los servicios coincidan."""

    ADMIN = "admin"
    USUARIO = "usuario"


class ClaimsToken(BaseModel):
    """Contenido (payload) validado de un token de acceso."""

    sub: str  # "subject": id del usuario (los claims estándar son strings)
    username: str
    rol: Rol
    iat: int  # "issued at": cuándo se emitió (segundos epoch)
    exp: int  # "expiration": cuándo caduca
    iss: str
    aud: str

    @property
    def usuario_id(self) -> int:
        return int(self.sub)


class TokenInvalido(Exception):
    """El token está mal formado, caducado, con firma incorrecta, etc."""


def crear_token_acceso(usuario_id: int, username: str, rol: Rol) -> tuple[str, int]:
    """Emite un token firmado. Devuelve (token, segundos_hasta_expirar)."""
    config = get_config_jwt()
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(minutes=config.jwt_minutos_expiracion)
    payload = {
        "sub": str(usuario_id),
        "username": username,
        "rol": str(rol),
        "iat": ahora,
        "exp": expira,
        "iss": config.jwt_emisor,
        "aud": config.jwt_audiencia,
    }
    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algoritmo)
    return token, config.jwt_minutos_expiracion * 60


def decodificar_token(token: str) -> ClaimsToken:
    """
    Valida el token y devuelve sus claims. PyJWT comprueba:
      - la firma (con la clave y SOLO el algoritmo configurado),
      - que no haya expirado (exp),
      - el emisor (iss) y la audiencia (aud),
      - que existan todos los claims obligatorios.
    Cualquier fallo -> TokenInvalido (el motivo exacto no se envía al cliente).
    """
    config = get_config_jwt()
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret_key,
            algorithms=[config.jwt_algoritmo],
            audience=config.jwt_audiencia,
            issuer=config.jwt_emisor,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        return ClaimsToken.model_validate(payload)
    except (jwt.PyJWTError, ValidationError, ValueError) as exc:
        raise TokenInvalido(str(exc)) from exc
