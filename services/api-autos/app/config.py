"""
config.py — Configuración centralizada de la aplicación.

Concepto clave: NUNCA escribir credenciales directamente en el código (OWASP:
"Security Misconfiguration" / exposición de secretos). En su lugar, se leen
desde variables de entorno o desde un archivo `.env` que no se versiona.

`pydantic-settings` hace esto por nosotros: declara una clase con los campos
esperados y Pydantic los lee, los valida y los convierte al tipo correcto.
Si falta una variable obligatoria, la app falla al arrancar (mejor que fallar
en mitad de una petición).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    # `env_file=".env"`: además de las variables de entorno del sistema, lee el
    # archivo .env. Las variables de entorno reales tienen prioridad.
    # `case_sensitive=False`: DB_HOST en el .env se asigna al campo db_host.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Base de datos (obligatorias salvo puerto) ---
    db_host: str
    db_port: int = 5432
    db_user: str
    db_pass: str
    db_database: str

    # --- CORS ---
    # Lista explícita de orígenes (dominios) que pueden llamar a la API desde
    # un navegador. Se puede sobrescribir con CORS_ORIGINS en formato JSON.
    cors_origins: list[str] = [
        "http://localhost:3000",  # React / Next.js
        "http://localhost:5173",  # Vite
        "http://localhost:8000",  # la propia API (Swagger UI)
    ]

    @property
    def database_url(self) -> URL:
        """
        Construye la URL de conexión con `URL.create` en lugar de concatenar
        strings: así caracteres especiales en la contraseña (@, :, /) se
        escapan correctamente.
        "postgresql+psycopg" = motor PostgreSQL usando el driver psycopg v3.
        """
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            port=self.db_port,
            database=self.db_database,
        )


@lru_cache
def get_settings() -> Settings:
    # `lru_cache` hace que el .env se lea una sola vez (patrón recomendado en
    # la documentación de FastAPI, sección "Settings and Environment Variables").
    return Settings()


settings = get_settings()
