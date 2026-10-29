"""
models.py — Tabla de la base de datos de api-usuarios.

La tabla "usuarios" vive en la MISMA base de datos que las tablas de
api-autos ("autos", esquema public), pero este servicio es su único dueño:
solo api-usuarios la lee, la escribe y la migra. No hay claves foráneas entre
tablas de servicios distintos (así cada servicio puede evolucionar solo).

Igual que en api-autos, aquí se describe CÓMO se guardan los datos; la
validación de lo que envía el cliente está en `schemas.py`.
"""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field, SQLModel

from auth_jwt import Rol


def ahora_utc() -> datetime:
    # Fechas SIEMPRE con zona horaria (UTC) para evitar ambigüedades.
    return datetime.now(UTC)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    # Restricciones en la base de datos (defensa en profundidad): aunque
    # Pydantic ya valida, PostgreSQL rechaza datos inválidos que lleguen por
    # cualquier otra vía.
    __table_args__ = (
        CheckConstraint("rol IN ('admin', 'usuario')", name="ck_usuarios_rol_valido"),
        # username y email se guardan en minúsculas: así "Ana" y "ana" no
        # pueden ser dos usuarios distintos.
        CheckConstraint("username = lower(username)", name="ck_usuarios_username_minusculas"),
        CheckConstraint("email = lower(email)", name="ck_usuarios_email_minusculas"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # unique=True + index=True: índice único. Los usuarios borrados (soft
    # delete) conservan su fila, así que su username/email siguen reservados.
    username: str = Field(max_length=30, unique=True, index=True)
    email: str = Field(max_length=254, unique=True, index=True)
    nombre_completo: str = Field(max_length=100)
    # Solo se guarda el HASH de la contraseña (Argon2id), nunca la contraseña.
    # Este campo jamás se incluye en las respuestas (ver UsuarioPublic).
    password_hash: str = Field(max_length=255)
    rol: str = Field(max_length=20, default=Rol.USUARIO)
    # Soft delete: en lugar de borrar la fila, se marca activo=False y se
    # guarda la fecha en eliminado_en. Se conserva el historial.
    activo: bool = Field(default=True)
    creado_en: datetime = Field(default_factory=ahora_utc, sa_type=DateTime(timezone=True))
    actualizado_en: datetime = Field(default_factory=ahora_utc, sa_type=DateTime(timezone=True))
    eliminado_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
