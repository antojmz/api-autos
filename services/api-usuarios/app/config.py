"""
config.py — Configuración centralizada de api-usuarios.

Igual que en api-autos: las credenciales NUNCA se escriben en el código. Se
leen de variables de entorno o del archivo `.env` (que no se versiona) con
`pydantic-settings`, que además las valida al arrancar.

La configuración JWT (JWT_SECRET_KEY, expiración, etc.) NO está aquí: vive en
la librería compartida `libs/auth-jwt` (auth_jwt.ConfigJWT), porque todos los
servicios deben usar exactamente los mismos valores.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Base de datos ---
    # Es la MISMA base de datos que usa api-autos ("autos", esquema public).
    # Este servicio solo crea y gestiona su propia tabla: "usuarios".
    db_host: str
    db_port: int = 5432
    db_user: str
    db_pass: str
    db_database: str

    # --- Administrador inicial ---
    # Si en la BD no existe ningún usuario con rol admin, al arrancar se crea
    # uno con estos datos (ver `crear_admin_inicial` en main.py). Son opcionales:
    # si no se definen, no se crea nada.
    # SecretStr: si alguien imprime la configuración (logs, errores), se
    # muestra "**********" en lugar de la contraseña.
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: SecretStr | None = None

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:3000",  # React / Next.js
        "http://localhost:5173",  # Vite
        "http://localhost:8001",  # la propia API (Swagger UI)
    ]

    @property
    def database_url(self) -> URL:
        """URL de conexión construida con `URL.create` (escapa caracteres especiales)."""
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
    return Settings()


settings = get_settings()
