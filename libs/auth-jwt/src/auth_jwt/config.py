"""
config.py — Configuración JWT leída de variables de entorno.

Todos los servicios deben usar EXACTAMENTE la misma JWT_SECRET_KEY, emisor y
audiencia: si no, los tokens que emite api-usuarios no serían válidos en el
resto. En Docker, docker-compose.yml inyecta JWT_SECRET_KEY desde el .env de
la raíz del monorepo a todos los servicios.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigJWT(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Clave para firmar (HS256 = HMAC con SHA-256). Mínimo 32 caracteres: una
    # clave corta se puede adivinar por fuerza bruta y falsificar tokens.
    jwt_secret_key: str = Field(min_length=32)
    # Algoritmo FIJO: al validar solo se acepta este. Así se evita el ataque
    # en el que el atacante cambia el header a "alg": "none".
    jwt_algoritmo: str = "HS256"
    # "iss" (issuer): quién emitió el token.
    jwt_emisor: str = "api-usuarios"
    # "aud" (audience): para quién es el token. Un token emitido para otro
    # sistema con la misma clave no se aceptaría aquí.
    jwt_audiencia: str = "monorepo-autos"
    # Tokens de corta duración: si se roban, sirven poco tiempo.
    jwt_minutos_expiracion: int = Field(default=30, ge=1, le=1440)


@lru_cache
def get_config_jwt() -> ConfigJWT:
    return ConfigJWT()
