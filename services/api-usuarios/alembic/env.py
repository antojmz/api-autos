"""
alembic/env.py — Configuración de Alembic para este proyecto.

Migraciones de api-usuarios. Alembic es la herramienta de migraciones recomendada por la documentación de
FastAPI/SQLAlchemy. Cada cambio de esquema (crear tabla, añadir columna...) se
guarda como un archivo en alembic/versions/ y se aplica con:
    alembic upgrade head      # aplica todas las migraciones pendientes
    alembic downgrade -1      # revierte la última
    alembic revision --autogenerate -m "mensaje"   # genera una nueva a partir
                                                   # de los cambios en app/models.py
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

from app import models  # noqa: F401

# Importar la configuración (lee .env) y los modelos. Importar app.models
# registra las tablas en SQLModel.metadata, que Alembic compara con la base
# de datos real para autogenerar migraciones.
from app.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


# La BD "autos" es COMPARTIDA con api-autos. Cada servicio lleva su propio
# historial de migraciones, así que cada uno necesita SU tabla de versiones:
# api-autos usa "alembic_version" (la de por defecto) y este servicio usa
# "alembic_version_usuarios". Si compartieran tabla, Alembic mezclaría las
# revisiones de ambos servicios.
VERSION_TABLE = "alembic_version_usuarios"


def incluir_objeto(objeto, nombre, tipo, reflejado, comparado_con) -> bool:
    """
    La BD "autos" es COMPARTIDA con otros servicios del monorepo (api-autos
    tiene ahí "autos" y "modelos"). Cada servicio gestiona solo
    SUS tablas: si una tabla existe en la BD (reflejado=True) pero no está en
    los modelos de este servicio (comparado_con=None), se ignora. Sin esto,
    `alembic revision --autogenerate` propondría borrar las tablas del otro
    servicio.
    """
    if tipo == "table" and reflejado and comparado_con is None:
        return False
    return True


def run_migrations_offline() -> None:
    """Modo 'offline': genera el SQL (alembic upgrade head --sql) sin conectarse."""
    context.configure(
        url=settings.database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        include_object=incluir_objeto,
        version_table=VERSION_TABLE,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo 'online': se conecta a PostgreSQL y aplica las migraciones."""
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=incluir_objeto,
            version_table=VERSION_TABLE,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
